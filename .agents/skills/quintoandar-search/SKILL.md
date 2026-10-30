---
name: quintoandar-search
version: 1.0.0
description: >
  Busca imóveis para alugar ou comprar no QuintoAndar (quintoandar.com.br) e lê os
  detalhes de um anúncio. Use sempre que a pessoa quiser procurar apartamento, casa
  ou kitnet no QuintoAndar, ou quando o /scrape rodar. Gatilhos: quintoandar, quinto
  andar, alugar apartamento, apartamento para alugar, aluguel sem fiador.
enabled: true
allowed-tools: Bash(python .agents/skills/quintoandar-search/cli.py *)
---

# QuintoAndar Search

Lê a página de resultados do QuintoAndar (dados server-side em `__NEXT_DATA__`).
Sem login, sem API key. Só Python 3.10+ (stdlib).

## Comandos

### Buscar

```bash
python .agents/skills/quintoandar-search/cli.py search --cidade "<cidade>" --uf <UF> [flags]
```

| Flag | Descrição |
|------|-----------|
| `--cidade` | **Obrigatória.** Ex.: `"São Paulo"`, `"Rio de Janeiro"`, `"Belo Horizonte"` |
| `--uf` | **Obrigatória.** Ex.: `SP`, `RJ`, `MG` |
| `--bairro` | Ex.: `"Pinheiros"`, `"Botafogo"`. Sem ele, busca a cidade toda |
| `--negocio` | `aluguel` (padrão) ou `venda` |
| `--tipo` | `apartamento` (padrão), `casa`, `kitnet` |
| `--quartos` | Mínimo de quartos (2 = 2 ou mais) |
| `--preco-min` / `--preco-max` | Faixa de **aluguel** (ou preço de venda) |
| `--total-max` | Custo total mensal máximo — filtro local |
| `--area-min` | m² mínimos — filtro local |
| `--vagas` | Vagas mínimas — filtro local |
| `--pets sim` | Só imóveis que aceitam pets |
| `--mobiliado sim\|nao` | Só mobiliados / só sem mobília |
| `--limit` | Máximo de resultados (padrão 24) |
| `--format` | `json` (padrão) ou `table` |

**Limite importante:** o QuintoAndar entrega ~24 imóveis por busca e não pagina no
servidor. Para cobrir mais, faça **várias buscas estreitas** (um bairro por chamada,
faixas de preço diferentes) em vez de uma larga.

O campo `condominio` nos resultados de busca é **condomínio + IPTU somados** (é assim
que o portal informa). `total` é o custo mensal: no aluguel, o pacote completo
(aluguel, condomínio, IPTU, seguro e taxa); na venda, condomínio + IPTU.

### Detalhes

```bash
python .agents/skills/quintoandar-search/cli.py detail <id-ou-url> [--negocio venda]
```

Use `--negocio venda` para imóveis vindos de busca de compra (alguns estão à venda e
para alugar; sem a flag, abre a versão de aluguel). Retorna descrição completa,
condomínio e IPTU separados, `aceita_pets`, `mobiliado`, comodidades presentes,
`elevador` (true/false/null), `suites`, `faixa_andar`, `perto_do_metro` e
`lugares_proximos`.

## Exemplos

```bash
# 2+ quartos em Pinheiros até R$ 4.000 de aluguel
python .agents/skills/quintoandar-search/cli.py search --cidade "São Paulo" --uf SP --bairro Pinheiros --quartos 2 --preco-max 4000 --format table

# Kitnet mobiliada em Botafogo, total até R$ 3.500
python .agents/skills/quintoandar-search/cli.py search --cidade "Rio de Janeiro" --uf RJ --bairro Botafogo --tipo kitnet --mobiliado sim --total-max 3500
```

## Erros (stderr JSON, exit 1)

| `code` | Significado | O que fazer |
|--------|-------------|-------------|
| `BAD_ARG` | Flag inválida ou faltando | Corrija a chamada; nunca invente flags |
| `FETCH_FAILED` | HTTP 404/erro de rede | Confira grafia de cidade/bairro |
| `BLOCKED` | HTTP 403 — portal recusou acesso automatizado | Não insista; use o fallback WebSearch |
| `NO_DATA` | Página sem `__NEXT_DATA__` | Layout mudou; avise a pessoa |
| `NOT_FOUND` | Anúncio removido | Marque como `indisponivel` |
