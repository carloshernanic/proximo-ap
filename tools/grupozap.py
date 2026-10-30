"""ZAP Imóveis and VivaReal run on the same engine and embed the same schema.org
JSON-LD in their result pages; only the URL layout differs. Both connectors share
this module.
"""
from __future__ import annotations

import re
import time
import urllib.parse

from http_util import (
    FetchError, StrictParser, apply_client_filters, emit, fail, fetch,
    json_ld_blocks, listing, positive_int, slugify, to_int, yes_no,
)

PORTALS = {
    "zap": {
        "base": "https://www.zapimoveis.com.br",
        "tipos": {"apartamento": "apartamentos", "casa": "casas"},
    },
    "vivareal": {
        "base": "https://www.vivareal.com.br",
        "tipos": {"apartamento": "apartamento_residencial", "casa": "casa_residencial"},
    },
}
AMENITY_PT = {
    "Pool": "piscina", "Gym": "academia", "Elevator": "elevador", "Concierge 24h": "portaria 24h",
    "Balcony": "varanda", "Gourmet Balcony": "varanda gourmet", "Barbecue Grill": "churrasqueira",
    "Party Hall": "salão de festas", "Playground": "playground", "Laundry": "lavanderia",
    "Service Area": "área de serviço", "Furnished": "mobiliado", "Pets Allowed": "aceita pets",
    "Air Conditioning": "ar-condicionado", "Builtin Wardrobe": "armários embutidos",
    "Gated Community": "condomínio fechado", "Sauna": "sauna", "Coworking": "coworking",
    "Garden": "jardim", "Sports Court": "quadra", "Bicycles Place": "bicicletário",
}


def build_search_url(portal: str, args, page: int) -> str:
    cfg = PORTALS[portal]
    negocio = "aluguel" if args.negocio == "aluguel" else "venda"
    tipo = cfg["tipos"][args.tipo]
    uf, cidade = args.uf.lower(), slugify(args.cidade)
    zona = slugify(args.zona) if args.zona else ""
    bairro = slugify(args.bairro) if args.bairro else ""
    if portal == "zap":
        place = f"{uf}+{cidade}"
        if bairro:
            place += f"+{zona}+{bairro}"  # empty zone ("++") works for cities without zones
        path = f"/{negocio}/{tipo}/{place}/"
    else:
        segments = [negocio, uf, cidade]
        if bairro:
            segments += [zona, bairro]
        path = "/" + "/".join(segments + [tipo]) + "/"
    query = {
        "quartos": args.quartos,
        "banheiros": args.banheiros,
        "vagas": args.vagas,
        "areaMinima": args.area_min,
        "areaMaxima": args.area_max,
        "precoMinimo": args.preco_min,
        "precoMaximo": args.preco_max,
        "pagina": page if page > 1 else None,
    }
    query = {k: v for k, v in query.items() if v is not None}
    return cfg["base"] + path + ("?" + urllib.parse.urlencode(query) if query else "")


def _count_from_name(name: str, word: str) -> int | None:
    match = re.search(rf"(\d+)\s+{word}", name)
    return int(match.group(1)) if match else None


def parse_product(product: dict, portal: str, negocio: str) -> dict:
    name = product.get("name") or ""
    offers = product.get("offers") or {}
    extra = offers.get("additionalProperty")
    extras = extra if isinstance(extra, list) else [extra] if isinstance(extra, dict) else []
    condo = iptu = None
    for prop in extras:
        label = (prop.get("name") or "").lower()
        if "condominium" in label:
            condo = to_int(prop.get("value"))
        elif "iptu" in label or "tax" in label:
            iptu = to_int(prop.get("value"))
    price = to_int(offers.get("price"))
    address = product.get("address") or {}
    amenities = [f.get("value") for f in product.get("amenityFeature") or [] if f.get("value")]
    bairro_match = re.search(r"\bem\s+(.+?),\s*[^,]+$", name)
    vagas = _count_from_name(name, "vaga")
    if vagas is None and "vaga" not in name:
        vagas = 0
    # Monthly cost: rent+fees when renting, only fees when buying.
    total = None
    if negocio == "aluguel" and price is not None:
        total = price + (condo or 0) + (iptu or 0)
    elif negocio == "venda" and (condo or iptu):
        total = (condo or 0) + (iptu or 0)
    return listing(
        id=f"{portal}-{product.get('@id')}",
        portal=portal,
        url=product.get("url") or offers.get("url"),
        titulo=name.strip(),
        tipo=(product.get("additionalType") or "").rsplit("/", 1)[-1] or None,
        negocio=negocio,
        aluguel=price if negocio == "aluguel" else None,
        preco_venda=price if negocio == "venda" else None,
        condominio=condo,
        iptu=iptu,
        total=total,
        area_m2=to_int((product.get("floorSize") or {}).get("value")),
        quartos=to_int(product.get("numberOfBedrooms")),
        banheiros=to_int(product.get("numberOfBathroomsTotal")),
        vagas=vagas,
        bairro=bairro_match.group(1).strip() if bairro_match else None,
        endereco=address.get("streetAddress"),
        cidade=address.get("addressLocality"),
        mobiliado=True if "Furnished" in amenities else None,
        aceita_pets=product.get("petsAllowed") if "petsAllowed" in product else None,
        comodidades=[AMENITY_PT.get(a, a) for a in amenities],
        descricao=(product.get("description") or "")[:600] or None,
        publicado_em=None,
    )


def parse_search_page(html: str, portal: str, negocio: str) -> tuple[list[dict], int | None]:
    for block in json_ld_blocks(html):
        if isinstance(block, dict) and block.get("@type") == "ItemList":
            products = [
                element.get("item") or {}
                for element in block.get("itemListElement") or []
            ]
            total_match = re.search(r"([\d.]+)\s+(?:an[uú]ncios|\w+\s+para)", block.get("description") or "")
            total = int(total_match.group(1).replace(".", "")) if total_match else None
            return [parse_product(p, portal, negocio) for p in products if p.get("@id")], total
    return [], None


def search(portal: str, args) -> dict:
    results, seen, total, first_url = [], set(), None, None
    for page in range(1, args.paginas + 1):
        url = build_search_url(portal, args, page)
        first_url = first_url or url
        try:
            _, html = fetch(url)
        except FetchError as exc:
            if exc.status == 403:
                # The portal is refusing automated access. Respect it: no retries,
                # /scrape falls back to WebSearch for this portal.
                if results:
                    break
                fail(f"{exc} - o portal bloqueou o acesso automatizado; use o fallback WebSearch", "BLOCKED")
            if exc.status == 404 and page == 1:
                hint = " - em capitais com zonas, informe --zona (ex.: zona-oeste)" if args.bairro else ""
                fail(f"{exc}{hint}", "NOT_FOUND")
            if page == 1:
                fail(str(exc), "FETCH_FAILED")
            break
        page_results, page_total = parse_search_page(html, portal, args.negocio)
        if page == 1 and not page_results:
            fail(f"sem JSON-LD de resultados em {url} - layout mudou ou não há imóveis", "NO_DATA")
        total = total or page_total
        new = [r for r in page_results if r["id"] not in seen]
        if not new:
            break
        seen.update(r["id"] for r in new)
        results.extend(new)
        if page < args.paginas:
            time.sleep(1.5)  # be polite between pages
    results = apply_client_filters(results, args)[: args.limit]
    return {"portal": portal, "url_busca": first_url, "total_portal": total, "results": results}


def detail(portal: str, args) -> dict:
    base = PORTALS[portal]["base"]
    url = args.id if args.id.startswith("http") else None
    if not url:
        fail("detail espera a URL completa do anúncio (campo url do search)", "BAD_ARG")
    if not url.startswith(base + "/imovel/"):
        fail(f"URL não é um anúncio de {base}", "BAD_ARG")
    try:
        final_url, html = fetch(url)
    except FetchError as exc:
        if exc.status == 403:
            fail(f"{exc} - o portal bloqueou o acesso automatizado; use os dados da busca ou WebFetch", "BLOCKED")
        fail(str(exc), "NOT_FOUND" if exc.status in (404, 410) else "FETCH_FAILED")
    product, description = None, None
    for block in json_ld_blocks(html):
        candidates = block if isinstance(block, list) else [block]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            if node.get("offers") and node.get("@id") and product is None:
                product = node
            if node.get("@type") == "RealEstateListing":
                for entity in node.get("mainEntity") or []:
                    if isinstance(entity, dict) and entity.get("description"):
                        description = entity["description"]
    if not product:
        # A 200 without listing data is usually an anti-bot challenge page, not a
        # removed listing - don't let /scrape mark it unavailable on this alone.
        fail(f"página sem dados do anúncio em {final_url} (desafio anti-bot ou layout novo)", "NO_DATA")
    item = parse_product(product, portal, args.negocio)
    if description:
        item["descricao"] = description
    item["url"] = final_url
    return {"portal": portal, "listing": item}


def main(portal: str) -> None:
    parser = StrictParser(prog=f"{portal}-search")
    sub = parser.add_subparsers(dest="command", required=True, parser_class=StrictParser)

    s = sub.add_parser("search", help="busca imóveis")
    s.add_argument("--cidade", required=True, help='ex.: "São Paulo"')
    s.add_argument("--uf", required=True, help="ex.: SP")
    s.add_argument("--zona", help="ex.: zona-oeste (obrigatória com --bairro em SP/RJ)")
    s.add_argument("--bairro", help='ex.: "Pinheiros"')
    s.add_argument("--negocio", choices=["aluguel", "venda"], default="aluguel")
    s.add_argument("--tipo", choices=sorted(PORTALS[portal]["tipos"]), default="apartamento")
    s.add_argument("--quartos", type=positive_int, help="mínimo de quartos")
    s.add_argument("--banheiros", type=positive_int)
    s.add_argument("--vagas", type=positive_int)
    s.add_argument("--area-min", type=positive_int)
    s.add_argument("--area-max", type=positive_int)
    s.add_argument("--preco-min", type=positive_int)
    s.add_argument("--preco-max", type=positive_int, help="aluguel (ou preço de venda) máximo")
    s.add_argument("--total-max", type=positive_int, help="aluguel+condomínio+IPTU máximo (filtro local)")
    s.add_argument("--pets", type=yes_no, help="sim = descarta quem não aceita pets (filtro local)")
    s.add_argument("--mobiliado", type=yes_no, help="filtro local")
    s.add_argument("--paginas", type=positive_int, default=1, help="páginas de ~30 imóveis (máx. 5)")
    s.add_argument("--limit", type=positive_int, default=60)
    s.add_argument("--format", choices=["json", "table"], default="json")

    d = sub.add_parser("detail", help="detalhes de um anúncio")
    d.add_argument("id", help="URL do anúncio")
    d.add_argument("--negocio", choices=["aluguel", "venda"], default="aluguel")
    d.add_argument("--format", choices=["json", "table"], default="json")

    args = parser.parse_args()
    if args.command == "search":
        if args.zona and not args.bairro:
            fail("--zona só faz sentido junto com --bairro", "BAD_ARG")
        if portal == "vivareal" and args.bairro and not args.zona:
            fail("no VivaReal, --bairro exige --zona; em cidades sem zonas busque a cidade inteira", "BAD_ARG")
        args.paginas = max(1, min(args.paginas, 5))
        payload = search(portal, args)
    else:
        payload = detail(portal, args)
    emit(payload, args.format)
