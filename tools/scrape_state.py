"""Dedup and storage for /scrape, so the growing history never enters the conversation.

    python tools/scrape_state.py candidates --results <hits.json>
    python tools/scrape_state.py store      --results <avaliados.json>
    python tools/scrape_state.py marcar     --id <id> --status <status> [--nota "..."]
    python tools/scrape_state.py listar     [--status novo] [--format json|table]

State lives in dados/vistos.json: {"vistos": {"<id>": {...listing, status, nota, ...}}}.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from http_util import fail, slugify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = Path(os.environ.get("PROXIMO_AP_STATE", ROOT / "dados" / "vistos.json"))
STATUSES = {"novo", "favorito", "contatado", "visita_agendada", "visitado", "proposta", "descartado", "indisponivel"}
REQUIRED = ("id", "portal", "url")


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"vistos": {}}
    with STATE_PATH.open(encoding="utf-8") as handle:
        state = json.load(handle)
    state.setdefault("vistos", {})
    return state


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_PATH.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_PATH)


def fingerprint(item: dict) -> str | None:
    """Same unit listed on several portals: street + area + price (rounded)."""
    street = item.get("endereco") or ""
    area = item.get("area_m2")
    price = item.get("aluguel") or item.get("preco_venda")
    if not street or not area or not price:
        return None
    return f"{slugify(street)}|{area}|{round(price / 50) * 50}"


def read_results(path: str) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"não consegui ler {path}: {exc}", "BAD_INPUT")
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    if not isinstance(data, list):
        fail("--results deve ser uma lista JSON de imóveis", "BAD_INPUT")
    return data


def split_new(items: list[dict], state: dict) -> tuple[list, list, list]:
    seen_ids = set(state["vistos"])
    seen_urls = {v.get("url") for v in state["vistos"].values()}
    seen_prints = {fingerprint(v) for v in state["vistos"].values()} - {None}
    selected, skipped, invalid = [], [], []
    for item in items:
        missing = [k for k in REQUIRED if not item.get(k)]
        if missing:
            invalid.append({"item": item.get("id") or item.get("url"), "faltando": missing})
            continue
        fp = fingerprint(item)
        if item["id"] in seen_ids or item["url"] in seen_urls:
            skipped.append({"id": item["id"], "motivo": "já visto"})
        elif fp and fp in seen_prints:
            skipped.append({"id": item["id"], "motivo": "mesmo imóvel em outro portal"})
        else:
            selected.append(item)
            seen_ids.add(item["id"])
            seen_urls.add(item["url"])
            if fp:
                seen_prints.add(fp)
    return selected, skipped, invalid


def cmd_candidates(args) -> dict:
    selected, skipped, invalid = split_new(read_results(args.results), load_state())
    return {"selected": selected, "skipped": skipped, "invalid": invalid}


def cmd_store(args) -> dict:
    state = load_state()
    selected, skipped, invalid = split_new(read_results(args.results), state)
    today = date.today().isoformat()
    for item in selected:
        entry = dict(item)
        entry.setdefault("status", "novo")
        if entry["status"] not in STATUSES:
            entry["status"] = "novo"
        entry["primeira_vez"] = today
        state["vistos"][item["id"]] = entry
    if selected:
        save_state(state)
    return {"added": [i["id"] for i in selected], "skipped": skipped, "invalid": invalid}


def cmd_marcar(args) -> dict:
    state = load_state()
    entry = state["vistos"].get(args.id)
    if entry is None:
        fail(f"id {args.id} não está em {STATE_PATH.name}", "NOT_FOUND")
    entry["status"] = args.status
    entry["atualizado_em"] = date.today().isoformat()
    if args.nota:
        entry.setdefault("notas", []).append(f"{entry['atualizado_em']}: {args.nota}")
    save_state(state)
    return {"id": args.id, "status": args.status}


def cmd_listar(args) -> dict:
    entries = list(load_state()["vistos"].values())
    if args.status:
        entries = [e for e in entries if e.get("status") == args.status]
    entries.sort(key=lambda e: e.get("nota_fit") or 0, reverse=True)
    return {"total": len(entries), "imoveis": entries}


def main() -> None:
    parser = argparse.ArgumentParser(prog="scrape_state")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("candidates", "store"):
        p = sub.add_parser(name)
        p.add_argument("--results", required=True)
    m = sub.add_parser("marcar")
    m.add_argument("--id", required=True)
    m.add_argument("--status", required=True, choices=sorted(STATUSES))
    m.add_argument("--nota")
    lst = sub.add_parser("listar")
    lst.add_argument("--status", choices=sorted(STATUSES))
    lst.add_argument("--format", choices=["json", "table"], default="json")
    args = parser.parse_args()

    handler = {"candidates": cmd_candidates, "store": cmd_store, "marcar": cmd_marcar, "listar": cmd_listar}
    result = handler[args.command](args)
    if args.command == "listar" and args.format == "table":
        for e in result["imoveis"]:
            print(f"{e.get('nota_fit', '-'):>4} | {e.get('status'):<15} | {e.get('total') or e.get('aluguel')} | {e.get('bairro')} | {e.get('url')}")
        return
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
