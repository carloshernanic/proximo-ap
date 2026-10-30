"""Shared helpers for the portal connectors (stdlib only).

Every connector prints one JSON document on stdout and, on failure, a JSON error on
stderr with exit code 1 — the same contract as the reference framework's portal CLIs,
so /scrape can treat all portals alike.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
RETRY_STATUSES = {429, 500, 502, 503, 504}

# Windows consoles default to cp1252; listings are full of accents.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass


class FetchError(Exception):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


def fetch(url: str, timeout: float = 25, retries: int = 2) -> tuple[str, str]:
    """GET a page like a browser would. Returns (final_url, html)."""
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "pt-BR,pt;q=0.9",
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8", errors="replace")
                return response.geturl(), body
        except urllib.error.HTTPError as exc:
            if exc.code in RETRY_STATUSES and attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise FetchError(f"HTTP {exc.code} for {url}", exc.code) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries:
                time.sleep(2 ** (attempt + 1))
                continue
            raise FetchError(f"network error for {url}: {exc}") from exc
    raise FetchError(f"gave up on {url}")


def json_ld_blocks(html: str) -> list:
    blocks = []
    for match in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S
    ):
        try:
            blocks.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return blocks


def next_data(html: str) -> dict | None:
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def to_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def listing(**fields) -> dict:
    """Normalized listing shape shared by every connector (missing = None).

    `total` is the monthly cost: rent + condo + IPTU when renting, condo + IPTU
    when buying.
    """
    keys = [
        "id", "portal", "url", "titulo", "tipo", "negocio",
        "aluguel", "preco_venda", "condominio", "iptu", "total",
        "area_m2", "quartos", "banheiros", "vagas",
        "bairro", "endereco", "cidade",
        "mobiliado", "aceita_pets", "comodidades", "descricao", "publicado_em",
    ]
    unknown = set(fields) - set(keys)
    if unknown:
        raise ValueError(f"unknown listing fields: {sorted(unknown)}")
    return {key: fields.get(key) for key in keys}


def fail(message: str, code: str) -> None:
    print(json.dumps({"error": message, "code": code}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def yes_no(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"sim", "s", "yes", "true", "1"}:
        return True
    if lowered in {"nao", "não", "n", "no", "false", "0"}:
        return False
    raise argparse.ArgumentTypeError("use sim ou nao")


def positive_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("deve ser >= 0")
    return number


class StrictParser(argparse.ArgumentParser):
    """argparse that reports errors as JSON on stderr, never silently."""

    def error(self, message: str) -> None:  # type: ignore[override]
        fail(f"{self.prog}: {message}", "BAD_ARG")


def apply_client_filters(results: list[dict], args) -> list[dict]:
    """Re-check every filter locally: portals treat some URL filters loosely."""
    kept = []
    for item in results:
        price = item["aluguel"] if item["negocio"] == "aluguel" else item["preco_venda"]
        if args.preco_min is not None and price is not None and price < args.preco_min:
            continue
        if args.preco_max is not None and price is not None and price > args.preco_max:
            continue
        if getattr(args, "total_max", None) is not None and item["total"] is not None and item["total"] > args.total_max:
            continue
        if args.quartos is not None and item["quartos"] is not None and item["quartos"] < args.quartos:
            continue
        if getattr(args, "area_min", None) is not None and item["area_m2"] is not None and item["area_m2"] < args.area_min:
            continue
        if getattr(args, "vagas", None) is not None and item["vagas"] is not None and item["vagas"] < args.vagas:
            continue
        if args.pets is True and item["aceita_pets"] is False:
            continue
        if args.mobiliado is True and item["mobiliado"] is not True:
            continue
        if args.mobiliado is False and item["mobiliado"] is True:
            continue
        kept.append(item)
    return kept


def money(value) -> str:
    return "-" if value is None else f"R$ {value:,.0f}".replace(",", ".")


def emit(payload: dict, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    results = payload.get("results")
    if results is None:  # detail
        item = payload["listing"]
        for key, value in item.items():
            if value not in (None, [], ""):
                print(f"{key:>12}: {value}")
        return
    print(f"{payload['portal']} | {len(results)} resultados | {payload['url_busca']}")
    for item in results:
        price = item["aluguel"] if item["negocio"] == "aluguel" else item["preco_venda"]
        print(
            f"- {money(price):>12} | total {money(item['total']):>12} | "
            f"{item['area_m2'] or '?'} m² | {item['quartos'] or '?'}q {item['vagas'] if item['vagas'] is not None else '?'}v | "
            f"{item['bairro'] or '?'} | {item['url']}"
        )
