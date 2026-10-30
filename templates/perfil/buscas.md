# Buscas por Portal

<!-- SETUP: gerado pelo /setup a partir de perfil/preferencias.md. Edite à vontade. -->

O `/scrape` descobre todo conector em `.agents/skills/*/SKILL.md` e roda as buscas
abaixo com as flags documentadas em cada SKILL.md. Portais sem conector (OLX,
Imovelweb, imobiliárias locais) usam as consultas `site:` da seção WebSearch.

**Regra de ouro:** buscas estreitas (um bairro por chamada) rendem mais que uma busca
larga — o QuintoAndar só entrega ~24 imóveis por chamada.

## Prioridade 1: bairros preferidos

```
quintoandar-search search --cidade "[CIDADE]" --uf [UF] --bairro "[BAIRRO_1]" --quartos [QUARTOS_MIN] --preco-max [ALUGUEL_MAX]
zap-search        search --cidade "[CIDADE]" --uf [UF] --zona [ZONA_1] --bairro "[BAIRRO_1]" --quartos [QUARTOS_MIN] --preco-max [ALUGUEL_MAX]
vivareal-search   search --cidade "[CIDADE]" --uf [UF] --zona [ZONA_1] --bairro "[BAIRRO_1]" --quartos [QUARTOS_MIN] --preco-max [ALUGUEL_MAX]
```

## Prioridade 2: bairros aceitáveis

```
quintoandar-search search --cidade "[CIDADE]" --uf [UF] --bairro "[BAIRRO_ACEITAVEL_1]" --quartos [QUARTOS_MIN] --preco-max [ALUGUEL_MAX]
```

## Prioridade 3: cidade inteira (rede larga)

```
zap-search search --cidade "[CIDADE]" --uf [UF] --quartos [QUARTOS_MIN] --preco-max [ALUGUEL_MAX] --area-min [AREA_MIN] --paginas 2
```

## WebSearch (portais sem conector)

```
site:olx.com.br/imoveis aluguel apartamento [QUARTOS_MIN] quartos [BAIRRO_1] [CIDADE]
site:imovelweb.com.br apartamento aluguel [BAIRRO_1] [CIDADE]
```

## Filtro de data
Anúncios sem data de publicação são aceitos. O dedup por `dados/vistos.json` garante
que o mesmo imóvel não aparece duas vezes entre execuções.
