"""QuintoAndar connector: search and detail via the server-rendered __NEXT_DATA__."""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))

from http_util import (  # noqa: E402
    FetchError, StrictParser, apply_client_filters, emit, fail, fetch, listing,
    next_data, positive_int, slugify, to_int, yes_no,
)

BASE = "https://www.quintoandar.com.br"
TIPOS = {"apartamento": "apartamento", "casa": "casa", "kitnet": "kitnet"}


def build_search_url(args) -> str:
    place = f"{slugify(args.cidade)}-{args.uf.lower()}-brasil"
    if args.bairro:
        place = f"{slugify(args.bairro)}-{place}"
    verb = "alugar" if args.negocio == "aluguel" else "comprar"
    parts = [BASE, verb, "imovel", place, TIPOS[args.tipo]]
    if args.quartos:
        parts.append("1-quarto" if args.quartos == 1 else f"{args.quartos}-quartos")
    if args.preco_max is not None:
        parts.append(f"de-{args.preco_min or 0}-a-{args.preco_max}-reais")
    if args.pets:
        parts.append("aceita-pets")
    if args.mobiliado:
        parts.append("mobiliado")
    return "/".join(parts)


def parse_house(house: dict, negocio: str, pets_filter: bool) -> dict:
    address = house.get("address") or {}
    rent = to_int(house.get("rentPrice"))
    total = to_int(house.get("totalCost"))
    condo_iptu = to_int(house.get("condoIptu"))
    return listing(
        id=f"quintoandar-{house['id']}",
        portal="quintoandar",
        url=f"{BASE}/imovel/{house['id']}" + ("" if negocio == "aluguel" else "/comprar"),
        titulo=house.get("shortRentDescription") if negocio == "aluguel" else house.get("shortSaleDescription"),
        tipo=house.get("type"),
        negocio=negocio,
        aluguel=rent,
        preco_venda=to_int(house.get("salePrice")) or None,
        # QuintoAndar only reports condo+IPTU combined in search results.
        condominio=condo_iptu,
        iptu=None,
        # Monthly cost: rent+fees when renting, only fees when buying.
        total=total if negocio == "aluguel" else condo_iptu,
        area_m2=to_int(house.get("area")),
        quartos=to_int(house.get("bedrooms")),
        banheiros=to_int(house.get("bathrooms")),
        vagas=to_int(house.get("parkingSpots")),
        bairro=house.get("neighbourhood") or house.get("regionName"),
        endereco=address.get("address"),
        cidade=address.get("city"),
        mobiliado=house.get("isFurnished"),
        # Search results carry no pet flag; the URL filter guarantees it when used.
        aceita_pets=True if pets_filter else None,
        comodidades=house.get("amenities") or [],
        descricao=None,
        publicado_em=None,
    )


def load_search_state(url: str) -> dict:
    try:
        _, html = fetch(url)
    except FetchError as exc:
        if exc.status == 403:
            fail(f"{exc} - o portal bloqueou o acesso automatizado; use o fallback WebSearch", "BLOCKED")
        fail(f"{exc} (cidade/bairro inexistente no QuintoAndar?)", "FETCH_FAILED")
    data = next_data(html)
    if not data:
        fail(f"no __NEXT_DATA__ in {url} - page layout changed or request blocked", "NO_DATA")
    return data["props"]["pageProps"].get("initialState") or {}


def search(args) -> dict:
    url = build_search_url(args)
    price_field = "aluguel" if args.negocio == "aluguel" else "preco_venda"
    # The server sometimes renders a total but houses without the requested price
    # (or none at all); a short pause and another request usually fixes it.
    for attempt in range(3):
        state = load_search_state(url)
        houses = state.get("houses") or {}
        visible = (state.get("search") or {}).get("visibleHouses") or {}
        order = (visible.get("pages") or {}).get("0") or list(houses)
        results = [
            parse_house(houses[house_id], args.negocio, bool(args.pets))
            for house_id in order
            if house_id in houses
        ]
        results = [r for r in results if r[price_field]]
        if results or not visible.get("total"):
            break
        time.sleep(2 * (attempt + 1))
    results = apply_client_filters(results, args)[: args.limit]
    return {
        "portal": "quintoandar",
        "url_busca": url,
        "total_portal": visible.get("total"),
        "results": results,
    }


def find_listing_node(node):
    """The detail page nests the house under a varying key; find it by its fields."""
    if isinstance(node, dict):
        if "condoPrice" in node and ("rentPrice" in node or "salePrice" in node) and "address" in node:
            return node
        for value in node.values():
            found = find_listing_node(value)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = find_listing_node(value)
            if found:
                return found
    return None


def detail(args) -> dict:
    match = re.search(r"(\d{6,})", args.id)
    if not match:
        fail("detail espera um id numérico ou URL do QuintoAndar", "BAD_ARG")
    house_id = match.group(1)
    # Rental listings resolve at /imovel/<id>; the sale view lives under
    # /imovel/<id>/comprar (sale-only listings 404 on the plain path).
    paths = [f"/imovel/{house_id}", f"/imovel/{house_id}/comprar"]
    if args.negocio == "venda":
        paths.reverse()
    final_url = html = None
    for path in paths:
        try:
            final_url, html = fetch(BASE + path, retries=0)
            break
        except FetchError as exc:
            if exc.status == 403:
                fail(f"{exc} - o portal bloqueou o acesso automatizado", "BLOCKED")
            if exc.status != 404:
                fail(str(exc), "FETCH_FAILED")
    if html is None:
        fail(f"anúncio {house_id} não existe mais", "NOT_FOUND")
    data = next_data(html)
    node = find_listing_node(data) if data else None
    if not node:
        fail(f"anúncio {house_id} sem dados (removido ou indisponível?)", "NOT_FOUND")
    flags = {}
    for value in node.values():
        if isinstance(value, list):
            for entry in value:
                if isinstance(entry, dict) and "key" in entry and "value" in entry:
                    flags[entry["key"]] = entry
    amenities = [e.get("text") or e["key"] for e in flags.values() if e["value"] == "SIM"]
    elevator = {"SIM": True, "NAO": False}.get((flags.get("ELEVADOR") or {}).get("value"))
    rent = to_int(node.get("rentPrice")) or None
    condo = to_int(node.get("condoPrice"))
    iptu = to_int(node.get("iptu"))
    region = node.get("region") or {}
    address = node.get("address") or {}
    if isinstance(address, dict) and address.get("street"):
        address = {**address, "address": address["street"]}
    is_rent = "/comprar" not in (final_url or "")
    item = listing(
        id=f"quintoandar-{house_id}",
        portal="quintoandar",
        url=final_url,
        titulo=node.get("shortRentDescription") or node.get("title"),
        tipo=node.get("type"),
        negocio="aluguel" if is_rent else "venda",
        aluguel=rent,
        preco_venda=to_int(node.get("salePrice")) or None,
        condominio=condo,
        iptu=iptu,
        total=(
            to_int(node.get("totalCost")) or (sum(v for v in (rent, condo, iptu) if v) or None)
            if is_rent else (sum(v for v in (condo, iptu) if v) or None)
        ),
        area_m2=to_int(node.get("area")),
        quartos=to_int(node.get("bedrooms")),
        banheiros=to_int(node.get("bathrooms")),
        vagas=to_int(node.get("parkingSpots", node.get("parkingSpaces"))),
        bairro=node.get("neighbourhood") or (address.get("neighborhood") if isinstance(address, dict) else None) or region.get("name"),
        endereco=address.get("address") if isinstance(address, dict) else address,
        cidade=node.get("city") or (address.get("city") if isinstance(address, dict) else None),
        mobiliado=node.get("hasFurniture"),
        aceita_pets=node.get("acceptsPets"),
        comodidades=amenities,
        descricao=node.get("remarks"),
        publicado_em=None,
    )
    nearby = [p.get("name") for p in node.get("placesNearby") or [] if isinstance(p, dict)]
    return {
        "portal": "quintoandar",
        "listing": item,
        "perto_do_metro": node.get("isNearSubway"),
        "lugares_proximos": nearby,
        "elevador": elevator,
        "suites": to_int(node.get("suites")),
        "faixa_andar": node.get("rangeFloor"),
    }


def main() -> None:
    parser = StrictParser(prog="quintoandar-search")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=StrictParser)

    s = sub.add_parser("search", help="busca imóveis")
    s.add_argument("--cidade", required=True, help='ex.: "São Paulo"')
    s.add_argument("--uf", required=True, help="ex.: SP")
    s.add_argument("--bairro", help='ex.: "Pinheiros"')
    s.add_argument("--negocio", choices=["aluguel", "venda"], default="aluguel")
    s.add_argument("--tipo", choices=sorted(TIPOS), default="apartamento")
    s.add_argument("--quartos", type=positive_int, help="mínimo de quartos")
    s.add_argument("--preco-min", type=positive_int)
    s.add_argument("--preco-max", type=positive_int, help="aluguel (ou preço de venda) máximo")
    s.add_argument("--total-max", type=positive_int, help="custo total mensal máximo (filtro local)")
    s.add_argument("--area-min", type=positive_int, help="filtro local")
    s.add_argument("--vagas", type=positive_int, help="mínimo de vagas (filtro local)")
    s.add_argument("--pets", type=yes_no, help="sim = só aceita pets")
    s.add_argument("--mobiliado", type=yes_no, help="sim = só mobiliado, nao = só sem mobília")
    s.add_argument("--limit", type=positive_int, default=24)
    s.add_argument("--format", choices=["json", "table"], default="json")

    d = sub.add_parser("detail", help="detalhes de um anúncio")
    d.add_argument("id", help="id numérico ou URL do anúncio")
    d.add_argument("--negocio", choices=["aluguel", "venda"], default="aluguel")
    d.add_argument("--format", choices=["json", "table"], default="json")

    args = parser.parse_args()
    payload = search(args) if args.command == "search" else detail(args)
    emit(payload, args.format)


if __name__ == "__main__":
    main()
