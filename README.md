# Próximo AP — busca de apartamento com IA (QuintoAndar, ZAP Imóveis, VivaReal)

[![tests](https://github.com/carloshernanic/proximo-ap/actions/workflows/tests.yml/badge.svg)](https://github.com/carloshernanic/proximo-ap/actions/workflows/tests.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![Sem dependências](https://img.shields.io/badge/depend%C3%AAncias-0-brightgreen)
![Licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

**Encontre apartamento para alugar ou comprar com um agente de IA.** O Próximo AP é um
workspace para o [Claude Code](https://claude.com/claude-code). Ele entrevista você
sobre o que procura e depois busca imóveis no **QuintoAndar**, no **ZAP Imóveis** e no
**VivaReal**. Remove anúncios repetidos entre portais, descarta o que não serve e dá uma
**nota de 0 a 100** para cada imóvel, usando os pesos que você escolheu.

> 🇬🇧 *AI-powered apartment hunting for Brazil. A Claude Code workspace that interviews
> you about your housing preferences, then searches QuintoAndar, ZAP Imóveis and
> VivaReal, deduplicates listings across portals and scores each one 0–100 against
> your criteria. Zero-dependency Python connectors. Inspired by
> [ai-job-search](https://github.com/ai-job-search-dev/ai-job-search).*

---

## Por que usar

- **Custo total, não só aluguel.** Compara aluguel + condomínio + IPTU. Na compra,
  compara preço e custo mensal.
- **Um imóvel, uma linha.** Detecta o mesmo apartamento anunciado no ZAP e no VivaReal.
- **Nunca mostra o mesmo imóvel duas vezes.** O histórico fica em `dados/vistos.json`.
- **Alertas de golpe.** Aponta preço muito abaixo do bairro, pedido de sinal antes da
  visita e anunciante que puxa a conversa para fora da plataforma.
- **Privado por padrão.** Suas preferências, seu histórico e seus relatórios ficam só na
  sua máquina (`.gitignore`).

## Como funciona

| Fase | Comando | O que faz |
|------|---------|-----------|
| **1. Preferências** | `/setup` | Entrevista em 6 blocos: objetivo, localização, orçamento, imóvel, prédio e pesos. Grava `perfil/preferencias.md` e as buscas em `perfil/buscas.md` |
| **2. Busca** | `/scrape` | Roda os conectores, remove duplicados, aplica os critérios eliminatórios, abre o detalhe dos melhores, dá nota e grava `relatorios/AAAA-MM-DD.md` |
| **3. Acompanhamento** | `scrape_state.py marcar` | Marca cada imóvel como favorito, visitado, proposta, descartado… |

## Começando

1. Instale o [Claude Code](https://claude.com/claude-code) e o Python 3.10+.
2. Clone e abra o repositório:
   ```bash
   git clone https://github.com/carloshernanic/proximo-ap.git
   ```
   ```bash
   cd proximo-ap && claude
   ```
3. No Claude Code, rode `/setup` e responda à entrevista.
4. Rode `/scrape`. Use `/scrape amplo` para buscar em todas as prioridades e
   `/scrape Moema` para focar num bairro.

## Conectores (portais imobiliários)

| Portal | Conector | Como lê | Observações |
|--------|----------|---------|-------------|
| QuintoAndar | `quintoandar-search` | Dados do Next.js (`__NEXT_DATA__`) | ~24 imóveis por busca. O detalhe traz pets, condomínio e IPTU separados e proximidade de metrô |
| ZAP Imóveis | `zap-search` | JSON-LD schema.org | ~30 por página, até 5 páginas |
| VivaReal | `vivareal-search` | JSON-LD schema.org | Mesmo motor do ZAP |
| OLX, Imovelweb, outros | — | WebSearch (`site:`) | Fallback |

Também dá para usar os conectores sem IA, direto no terminal:

```bash
python .agents/skills/quintoandar-search/cli.py search --cidade "São Paulo" --uf SP --bairro Pinheiros --quartos 2 --preco-max 4000 --format table
```

```bash
python .agents/skills/zap-search/cli.py search --cidade Campinas --uf SP --negocio venda --preco-max 800000 --area-min 60 --format table
```

Flags e códigos de erro de cada conector estão no `SKILL.md` dele.

> **Sobre bloqueios:** ZAP e VivaReal às vezes respondem HTTP 403 a acessos
> automatizados. Nesse caso, o conector devolve `BLOCKED` e o `/scrape` usa o WebSearch
> para aquele portal. O projeto **não** tenta contornar proteções anti-bot.

## Estrutura

```
.agents/skills/<portal>-search/   conectores (SKILL.md + cli.py)
.claude/commands/setup.md         fase 1: entrevista de preferências
.claude/skills/scraper/SKILL.md   fase 2: /scrape
templates/perfil/                 modelos de preferências e buscas
perfil/                           suas preferências (ignorado pelo git)
dados/vistos.json                 histórico de imóveis (ignorado pelo git)
relatorios/                       relatório por execução (ignorado pelo git)
tools/                            HTTP, parser ZAP/VivaReal, deduplicação
tests/                            testes offline
```

## Acompanhar imóveis

```bash
python tools/scrape_state.py listar --format table
```

```bash
python tools/scrape_state.py marcar --id quintoandar-892930376 --status favorito --nota "gostei da varanda"
```

Status: `novo`, `favorito`, `contatado`, `visita_agendada`, `visitado`, `proposta`,
`descartado`, `indisponivel`.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Contribuindo

Novos portais são bem-vindos (OLX, Imovelweb, Loft, imobiliárias regionais). Veja o
[CONTRIBUTING.md](CONTRIBUTING.md).

## Uso responsável

Os conectores fazem poucas requisições, com pausa entre páginas, e só leem páginas
públicas permitidas pelo `robots.txt`. Use para a sua busca pessoal, não para coleta
em massa nem revenda de dados. Os termos de uso de cada portal valem para você. Este
projeto não tem relação com QuintoAndar, Grupo OLX, ZAP Imóveis ou VivaReal.

## Licença

[MIT](LICENSE)

---

<sub>Palavras-chave: busca de apartamento, encontrar apartamento, apartamento para
alugar, comprar apartamento, imóveis São Paulo, scraper QuintoAndar, scraper ZAP
Imóveis, scraper VivaReal, agente de IA imobiliário, Claude Code, house hunting
Brazil, real estate scraper Brazil.</sub>
