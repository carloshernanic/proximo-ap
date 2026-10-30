---
name: vivareal-search
version: 1.0.0
description: >
  Busca imóveis para alugar ou comprar no VivaReal (vivareal.com.br) e lê os detalhes
  de um anúncio. Use quando a pessoa quiser procurar imóveis no VivaReal ou quando o
  /scrape rodar. Gatilhos: vivareal, viva real, apartamento para alugar, imóveis.
enabled: true
allowed-tools: Bash(python .agents/skills/vivareal-search/cli.py *)
---

# VivaReal Search

Mesmo motor e mesmas flags do `zap-search` (código em `tools/grupozap.py`). Muitos
anúncios aparecem nos dois portais — o `/scrape` deduplica por endereço + área + preço.

```bash
python .agents/skills/vivareal-search/cli.py search --cidade "<cidade>" --uf <UF> [flags]
python .agents/skills/vivareal-search/cli.py detail "<url do anúncio>"
```

Flags: idênticas às do `zap-search` (veja `.agents/skills/zap-search/SKILL.md`), com
uma diferença:

- **`--bairro` exige `--zona`** (`zona-oeste`, `zona-sul`, …). Em cidades sem zonas,
  busque a cidade inteira (sem `--bairro`) e filtre pelo campo `bairro` dos resultados,
  ou use o `zap-search`, que aceita bairro sem zona.

## Exemplo

```bash
python .agents/skills/vivareal-search/cli.py search --cidade "São Paulo" --uf SP --zona zona-sul --bairro "Vila Mariana" --quartos 2 --total-max 4500 --format table
```

## Erros

Mesmos códigos do `zap-search`. Em `BLOCKED` (403), não insista: use o fallback
WebSearch para este portal nesta execução.
