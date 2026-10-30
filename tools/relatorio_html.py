"""Render a /scrape run as a self-contained HTML page with listing photos.

    python tools/relatorio_html.py [--data AAAA-MM-DD] [--saida relatorios/AAAA-MM-DD.html]

Reads dados/vistos.json (never the network). Photos are hot-linked from the
portal CDNs, so the page needs internet to show them.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import scrape_state  # noqa: E402
from http_util import money  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PORTAL_NAMES = {"quintoandar": "QuintoAndar", "zap": "ZAP Imóveis", "vivareal": "VivaReal"}


def full_size(url: str) -> str:
    return url.replace("/img/lrg/", "/img/xxl/")


def fit_class(entry: dict) -> str:
    return {"alto": "alto", "medio": "medio"}.get(entry.get("fit"), "baixo")


def bullet_list(items, css: str) -> str:
    items = [i for i in items or [] if i]
    if not items:
        return ""
    lis = "".join(f"<li>{escape(i)}</li>" for i in items)
    return f'<ul class="{css}">{lis}</ul>'


def gallery(entry: dict) -> str:
    photos = entry.get("fotos") or []
    if not photos:
        return '<div class="gallery empty"><span>Sem fotos</span></div>'
    slides = []
    for index, photo in enumerate(photos, 1):
        caption = escape(photo.get("legenda") or "")
        alt = escape(f"Foto {index} – {photo.get('legenda') or entry.get('bairro') or ''}")
        slides.append(
            f'<a class="slide" href="{escape(full_size(photo["url"]))}" target="_blank" rel="noopener noreferrer">'
            f'<img src="{escape(photo["url"])}" alt="{alt}" loading="lazy" referrerpolicy="no-referrer">'
            + (f"<span class=\"caption\">{caption}</span>" if caption else "")
            + f'<span class="count">{index}/{len(photos)}</span></a>'
        )
    arrows = (
        '<button type="button" class="nav prev" aria-label="Foto anterior">‹</button>'
        '<button type="button" class="nav next" aria-label="Próxima foto">›</button>'
        if len(photos) > 1 else ""
    )
    return (
        f'<div class="gallery-wrap"><div class="gallery" tabindex="0" aria-label="Fotos">'
        f'{"".join(slides)}</div>{arrows}</div>'
    )


def card(entry: dict) -> str:
    sale = entry.get("negocio") == "venda"
    price = entry.get("preco_venda") if sale else entry.get("aluguel")
    monthly_label = "cond. + IPTU" if sale else "total/mês"
    facts = [
        f"{entry.get('area_m2') or '?'} m²",
        f"{entry.get('quartos') or '?'} quarto{'s' if (entry.get('quartos') or 0) != 1 else ''}",
    ]
    if entry.get("suites"):
        facts.append(f"{entry['suites']} suíte{'s' if entry['suites'] > 1 else ''}")
    facts.append(f"{entry.get('vagas') if entry.get('vagas') is not None else '?'} vaga{'s' if entry.get('vagas') != 1 else ''}")
    floor = entry.get("faixa_andar") or {}
    if floor.get("max"):
        facts.append(f"andar {floor.get('min')}–{floor.get('max')}")
    if entry.get("elevador") is True:
        facts.append("elevador")
    chips = "".join(f"<span>{escape(f)}</span>" for f in facts)
    verified = '<span class="tag ok">detalhe verificado</span>' if entry.get("detalhado") else '<span class="tag">só dados da busca</span>'
    place = ", ".join(p for p in (entry.get("endereco"), entry.get("bairro")) if p)
    return f"""
<article class="card {fit_class(entry)}" data-bairro="{escape(entry.get('bairro') or '')}" data-quartos="{entry.get('quartos') or 0}">
  {gallery(entry)}
  <div class="body">
    <div class="top">
      <div class="score" title="Nota de 0 a 100">{entry.get('nota_fit', '–')}</div>
      <div class="money">
        <strong>{money(price)}</strong>
        <small>{money(entry.get('total'))} {monthly_label}</small>
      </div>
    </div>
    <h3>{escape(place or entry.get('titulo') or 'Imóvel')}</h3>
    <div class="facts">{chips}</div>
    <p class="commute">{escape(entry.get('deslocamento') or '')}</p>
    {bullet_list(entry.get('pontos_fortes'), 'pros')}
    {bullet_list(entry.get('pontos_fracos'), 'cons')}
    {bullet_list(entry.get('alertas'), 'alerts')}
    <div class="foot">
      {verified}
      <a class="cta" href="{escape(entry['url'])}" target="_blank" rel="noopener noreferrer">Ver no {escape(PORTAL_NAMES.get(entry.get('portal'), entry.get('portal') or 'portal'))} →</a>
    </div>
  </div>
</article>"""


def render(entries: list[dict], run_date: str) -> str:
    ranked = sorted((e for e in entries if e.get("nota_fit") is not None), key=lambda e: -e["nota_fit"])
    discarded = [e for e in entries if e.get("status") == "descartado"]
    portals = sorted({PORTAL_NAMES.get(e.get("portal"), e.get("portal")) for e in entries})
    neighbourhoods = sorted({e.get("bairro") for e in ranked if e.get("bairro")})
    filters = "".join(
        f'<button type="button" data-filter="{escape(b)}">{escape(b)}</button>' for b in neighbourhoods
    )
    discarded_rows = "".join(
        f"<tr><td>{escape(e.get('bairro') or '')}</td><td>{money(e.get('preco_venda') or e.get('aluguel'))}</td>"
        f"<td>{e.get('area_m2') or '?'} m²</td><td>{escape(e.get('motivo_descarte') or '')}</td>"
        f'<td><a href="{escape(e["url"])}" target="_blank" rel="noopener noreferrer">anúncio</a></td></tr>'
        for e in discarded
    )
    day = date.fromisoformat(run_date).strftime("%d/%m/%Y")
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>Próximo AP – {day}</title>
<style>
:root {{
  --bg: #f6f3ee; --surface: #fffdf9; --ink: #1f1b16; --muted: #6b6259; --line: #e6dfd4;
  --accent: #b4532a; --alto: #2f7d4f; --medio: #b7791f; --baixo: #9b3b3b;
  --pros: #2f7d4f; --cons: #8a6d3b; --alerts: #b4532a; --chip: #efe8dd;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #15120f; --surface: #1e1a16; --ink: #f1ebe3; --muted: #a89d90; --line: #332c25;
    --accent: #e0814f; --alto: #5fbf86; --medio: #e0a84a; --baixo: #e07a7a;
    --pros: #5fbf86; --cons: #d2b07a; --alerts: #e0814f; --chip: #2a241e;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
header, main, footer {{ max-width: 1180px; margin: 0 auto; padding: 0 16px; }}
header {{ padding-top: 40px; padding-bottom: 8px; }}
h1 {{ font-size: clamp(28px, 4vw, 40px); line-height: 1.1; margin: 0 0 6px; letter-spacing: -0.02em; }}
.sub {{ color: var(--muted); margin: 0 0 20px; }}
.stats {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
.stats div {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 10px 16px; }}
.stats strong {{ display: block; font-size: 22px; }}
.stats span {{ color: var(--muted); font-size: 13px; }}
.filters {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px; }}
.filters button {{ border: 1px solid var(--line); background: var(--surface); color: var(--ink);
  border-radius: 999px; padding: 6px 14px; cursor: pointer; font: inherit; }}
.filters button[aria-pressed="true"] {{ background: var(--ink); color: var(--bg); border-color: var(--ink); }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; overflow: hidden;
  display: flex; flex-direction: column; }}
.card[hidden] {{ display: none; }}
.gallery {{ display: flex; overflow-x: auto; scroll-snap-type: x mandatory; aspect-ratio: 4 / 3;
  background: var(--chip); scrollbar-width: thin; }}
.gallery.empty {{ align-items: center; justify-content: center; color: var(--muted); }}
.gallery-wrap {{ position: relative; }}
.nav {{ position: absolute; top: 50%; transform: translateY(-50%); width: 36px; height: 36px;
  border-radius: 50%; border: 0; background: rgba(255,255,255,.85); color: #1f1b16;
  font-size: 22px; line-height: 1; cursor: pointer; opacity: 0; transition: opacity .15s; }}
.nav.prev {{ left: 10px; }}
.nav.next {{ right: 10px; }}
.gallery-wrap:hover .nav, .nav:focus-visible {{ opacity: 1; }}
@media (hover: none) {{ .nav {{ display: none; }} }}
.slide {{ position: relative; flex: 0 0 100%; scroll-snap-align: start; }}
.slide img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
.caption, .count {{ position: absolute; bottom: 10px; font-size: 12px; color: #fff;
  background: rgba(0,0,0,.55); padding: 2px 8px; border-radius: 6px; }}
.caption {{ left: 10px; }}
.count {{ right: 10px; }}
.body {{ padding: 16px 18px 18px; display: flex; flex-direction: column; gap: 8px; flex: 1; }}
.top {{ display: flex; align-items: center; gap: 14px; }}
.score {{ width: 52px; height: 52px; border-radius: 50%; display: grid; place-items: center;
  font-weight: 700; font-size: 19px; color: #fff; background: var(--baixo); flex: none; }}
.alto .score {{ background: var(--alto); }}
.medio .score {{ background: var(--medio); }}
.money strong {{ font-size: 22px; display: block; letter-spacing: -0.01em; }}
.money small {{ color: var(--muted); }}
h3 {{ margin: 4px 0 0; font-size: 16px; }}
.facts {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.facts span {{ background: var(--chip); border-radius: 6px; padding: 2px 8px; font-size: 13px; }}
.commute {{ margin: 0; color: var(--muted); font-size: 13px; }}
ul {{ margin: 0; padding-left: 20px; font-size: 14px; }}
ul.pros li::marker {{ content: "+  "; color: var(--pros); font-weight: 700; }}
ul.cons li::marker {{ content: "–  "; color: var(--cons); font-weight: 700; }}
ul.alerts li::marker {{ content: "!  "; color: var(--alerts); font-weight: 700; }}
ul.alerts {{ color: var(--alerts); }}
.foot {{ margin-top: auto; padding-top: 10px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }}
.tag {{ font-size: 12px; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px; }}
.tag.ok {{ color: var(--alto); border-color: currentColor; }}
.cta {{ color: var(--accent); font-weight: 600; text-decoration: none; }}
.cta:hover {{ text-decoration: underline; }}
section.discarded {{ margin-top: 40px; }}
details {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px 16px; }}
summary {{ cursor: pointer; font-weight: 600; }}
.table-wrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 14px; }}
td {{ border-top: 1px solid var(--line); padding: 8px 10px 8px 0; vertical-align: top; }}
td a {{ color: var(--accent); }}
footer {{ color: var(--muted); font-size: 13px; padding-top: 32px; padding-bottom: 40px; }}
@media (max-width: 420px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<header>
  <h1>Próximo AP</h1>
  <p class="sub">Busca de {day} · {escape(', '.join(portals))}</p>
  <div class="stats">
    <div><strong>{len(entries)}</strong><span>imóveis novos</span></div>
    <div><strong>{len(ranked)}</strong><span>avaliados</span></div>
    <div><strong>{sum(1 for e in ranked if e.get('fit') == 'alto')}</strong><span>nota alta (75+)</span></div>
    <div><strong>{len(discarded)}</strong><span>descartados</span></div>
  </div>
  <div class="filters" role="group" aria-label="Filtrar por bairro">
    <button type="button" data-filter="" aria-pressed="true">Todos</button>{filters}
  </div>
</header>
<main>
  <div class="grid">{''.join(card(e) for e in ranked)}</div>
  <section class="discarded">
    <details>
      <summary>Descartados ({len(discarded)})</summary>
      <div class="table-wrap"><table><tbody>{discarded_rows}</tbody></table></div>
    </details>
  </section>
</main>
<footer>
  Fotos e dados dos anúncios pertencem aos portais e anunciantes. Deslocamentos são estimativas.
  Gerado pelo Próximo AP.
</footer>
<script>
document.querySelectorAll('.filters button').forEach(function (button) {{
  button.addEventListener('click', function () {{
    document.querySelectorAll('.filters button').forEach(function (b) {{ b.setAttribute('aria-pressed', b === button); }});
    var value = button.dataset.filter;
    document.querySelectorAll('.card').forEach(function (c) {{ c.hidden = value && c.dataset.bairro !== value; }});
  }});
}});
document.querySelectorAll('.nav').forEach(function (button) {{
  button.addEventListener('click', function () {{
    var gallery = button.parentElement.querySelector('.gallery');
    var step = button.classList.contains('next') ? 1 : -1;
    gallery.scrollBy({{ left: step * gallery.clientWidth, behavior: 'smooth' }});
  }});
}});
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(prog="relatorio_html")
    parser.add_argument("--data", default=date.today().isoformat(), help="data da execução (primeira_vez)")
    parser.add_argument("--saida", help="arquivo de saída (padrão relatorios/<data>.html)")
    args = parser.parse_args()
    entries = [e for e in scrape_state.load_state()["vistos"].values() if e.get("primeira_vez") == args.data]
    if not entries:
        print(json.dumps({"error": f"nenhum imóvel visto em {args.data}", "code": "NO_DATA"}), file=sys.stderr)
        sys.exit(1)
    out = Path(args.saida) if args.saida else ROOT / "relatorios" / f"{args.data}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(entries, args.data), encoding="utf-8")
    print(json.dumps({"arquivo": str(out), "imoveis": len(entries)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
