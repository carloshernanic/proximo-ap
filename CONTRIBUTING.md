# Contribuindo

Valeu pelo interesse! As contribuições mais úteis são **novos conectores de portais**
(OLX, Imovelweb, Loft, imobiliárias regionais) e correções quando um portal muda o
layout.

## Rodando localmente

```bash
python -m unittest discover -s tests -v
```

Só Python 3.10+, sem dependências. Os testes são offline: nunca acessam a rede.

## Adicionando um portal

1. Crie `.agents/skills/<portal>-search/` com:
   - `cli.py` com os subcomandos `search` e `detail`, usando `StrictParser`, `fetch`,
     `listing()` e `fail()` de `tools/http_util.py`;
   - `SKILL.md` com frontmatter (`name`, `description`, `enabled: true`,
     `allowed-tools`) e a tabela de flags.
2. Saída: `{"portal", "url_busca", "total_portal", "results": [...]}` no stdout; erros
   como JSON no stderr com exit 1 e um destes códigos: `BAD_ARG`, `NOT_FOUND`,
   `BLOCKED`, `FETCH_FAILED`, `NO_DATA`.
3. Adicione testes em `tests/` com HTML **sintético** (nada de páginas reais
   salvas — elas contêm dados de anunciantes).
4. O `/scrape` descobre o conector sozinho.

## Regras para conectores

- Leia só páginas públicas permitidas pelo `robots.txt` do portal.
- Poucas requisições, com pausa entre páginas. Nada de paralelismo no mesmo portal.
- **Não contorne bloqueios.** HTTP 403, captcha ou desafio anti-bot → devolva
  `BLOCKED` e deixe o `/scrape` usar o fallback WebSearch. PRs que tentem burlar
  proteção de portal não serão aceitos.
- Nunca invente campos: o que o portal não informa fica `null`.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/pt-br/):
`feat(zap): ...`, `fix(quintoandar): ...`, `docs: ...`, `test: ...`, `ci: ...`.
