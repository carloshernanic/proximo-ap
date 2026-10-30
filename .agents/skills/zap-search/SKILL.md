---
name: zap-search
version: 1.0.0
description: >
  Busca imóveis para alugar ou comprar no ZAP Imóveis (zapimoveis.com.br) e lê os
  detalhes de um anúncio. Use quando a pessoa quiser procurar imóveis no ZAP ou quando
  o /scrape rodar. Gatilhos: zap, zap imóveis, zapimoveis, apartamento para alugar,
  imóveis à venda.
enabled: true
allowed-tools: Bash(python .agents/skills/zap-search/cli.py *)
---

# ZAP Imóveis Search

Lê os dados schema.org (JSON-LD) da página de resultados do ZAP. ~30 imóveis por
página. Mesmo motor do VivaReal (código compartilhado em `tools/grupozap.py`).

## Comandos

### Buscar

```bash
python .agents/skills/zap-search/cli.py search --cidade "<cidade>" --uf <UF> [flags]
```

| Flag | Descrição |
|------|-----------|
| `--cidade`, `--uf` | **Obrigatórias** |
| `--bairro` | Ex.: `"Pinheiros"` |
| `--zona` | **Obrigatória com `--bairro` em São Paulo e Rio**: `zona-oeste`, `zona-sul`, `zona-norte`, `zona-leste`, `centro`. Em cidades sem zonas (Campinas, Curitiba…) omita |
| `--negocio` | `aluguel` (padrão) ou `venda` |
| `--tipo` | `apartamento` (padrão) ou `casa` |
| `--quartos`, `--banheiros`, `--vagas` | Mínimos |
| `--area-min`, `--area-max` | m² |
| `--preco-min`, `--preco-max` | Faixa de aluguel (ou venda) |
| `--total-max` | Aluguel + condomínio + IPTU — filtro local |
| `--pets sim` | Descarta quem declara não aceitar pets — filtro local |
| `--mobiliado sim\|nao` | Filtro local pelo item "mobiliado" das comodidades |
| `--paginas` | Páginas a ler (1–5, padrão 1). Pausa de 1,5 s entre páginas |
| `--limit` | Máximo de resultados (padrão 60) |
| `--format` | `json` (padrão) ou `table` |

`vagas` é extraído do título do anúncio. O IPTU raramente vem nos resultados — quando
falta, `total` = aluguel + condomínio, e o `/scrape` sinaliza "IPTU não informado".

### Detalhes

```bash
python .agents/skills/zap-search/cli.py detail "<url do anúncio>"
```

Retorna a descrição completa do anunciante e os mesmos campos da busca.

## Exemplos

```bash
python .agents/skills/zap-search/cli.py search --cidade "São Paulo" --uf SP --zona zona-oeste --bairro Pinheiros --quartos 2 --preco-max 4000 --format table
python .agents/skills/zap-search/cli.py search --cidade Campinas --uf SP --bairro "Cambuí" --quartos 1 --total-max 3000
```

## Erros (stderr JSON, exit 1)

| `code` | Significado | O que fazer |
|--------|-------------|-------------|
| `BAD_ARG` | Flag inválida | Corrija; nunca invente flags |
| `NOT_FOUND` | 404 — combinação cidade/zona/bairro não existe | Confira a zona do bairro |
| `BLOCKED` | 403 — o ZAP recusou acesso automatizado | **Não tente contornar nem repetir em loop.** Use o fallback WebSearch para este portal nesta execução |
| `FETCH_FAILED` | Erro de rede | Registre e siga |
| `NO_DATA` | Página sem dados estruturados | Na busca: layout mudou ou não há imóveis. No `detail`: geralmente é página de desafio anti-bot — **não** marque o imóvel como indisponível; use os dados da busca |
