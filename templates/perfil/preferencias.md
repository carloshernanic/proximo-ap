# Preferências de Apartamento

<!-- SETUP: este arquivo é preenchido pelo /setup. Você também pode editá-lo à mão. -->
<!-- Todo [PLACEHOLDER] ainda não respondido significa "sem preferência" para o /scrape. -->

## Objetivo
- **Negócio:** [ALUGAR_OU_COMPRAR] <!-- alugar | comprar -->
- **Prazo de mudança:** [DATA_OU_PRAZO]
- **Quem vai morar:** [MORADORES] <!-- ex.: "eu + parceira + 1 gato" -->

## Localização
- **Cidade / UF:** [CIDADE], [UF]
- **Bairros preferidos (em ordem):** [BAIRROS_PREFERIDOS]
- **Bairros aceitáveis:** [BAIRROS_ACEITAVEIS]
- **Bairros vetados:** [BAIRROS_VETADOS]
- **Pontos de referência e tempo máximo de deslocamento:**
  | Lugar | Endereço | Tempo máx. | Modo |
  |-------|----------|-----------|------|
  | [LUGAR] | [ENDERECO] | [MIN] min | [METRO_CARRO_A_PE_BIKE] |
- **Perto de metrô/trem é:** [OBRIGATORIO_DESEJAVEL_INDIFERENTE]

## Orçamento
<!-- Preencha só a parte do negócio escolhido; apague a outra. -->
### Se for alugar
- **Custo total mensal máximo (aluguel + condomínio + IPTU):** R$ [TOTAL_MAX]
- **Custo total ideal:** R$ [TOTAL_IDEAL]
- **Aluguel mínimo** (abaixo disso desconfiar): R$ [ALUGUEL_MIN]
- **Garantia aceita:** [GARANTIAS] <!-- fiador, seguro-fiança, caução, sem garantia (QuintoAndar) -->

### Se for comprar
- **Preço de compra máximo:** R$ [PRECO_COMPRA_MAX]
- **Preço de compra ideal:** R$ [PRECO_COMPRA_IDEAL]
- **Condomínio + IPTU mensal máximo:** R$ [CUSTO_MENSAL_MAX]
- **Forma de pagamento:** [PAGAMENTO] <!-- financiamento, à vista, permuta, indefinido -->

## O imóvel
- **Tipos aceitos:** [TIPOS] <!-- apartamento, studio/kitnet, casa de condomínio, cobertura -->
- **Quartos (mín.):** [QUARTOS_MIN]
- **Suítes (mín.):** [SUITES_MIN]
- **Banheiros (mín.):** [BANHEIROS_MIN]
- **Vagas de garagem (mín.):** [VAGAS_MIN]
- **Área útil (m²):** mín. [AREA_MIN] / ideal [AREA_IDEAL]
- **Mobiliado:** [SIM_NAO_INDIFERENTE]
- **Aceita pets:** [OBRIGATORIO_INDIFERENTE]
- **Andar:** [PREFERENCIA_ANDAR] <!-- ex.: "não térreo", "andar alto" -->

## Prédio e condomínio
- **Obrigatórios (deal-breakers):** [OBRIGATORIOS] <!-- ex.: portaria 24h, elevador -->
- **Desejáveis (somam pontos):** [DESEJAVEIS] <!-- ex.: varanda, academia, piscina, lavanderia -->
- **Vetos:** [VETOS] <!-- ex.: sem elevador acima do 3º andar, rua muito barulhenta -->

## Pesos para a nota (0–100)
<!-- O /scrape usa estes pesos na avaliação rápida. Somam 100. -->
| Critério | Peso |
|----------|------|
| Preço total vs. orçamento | [PESO_PRECO] |
| Localização / deslocamento | [PESO_LOCAL] |
| Tamanho e cômodos | [PESO_TAMANHO] |
| Prédio / comodidades | [PESO_PREDIO] |
| Estado de conservação / fotos | [PESO_ESTADO] |

## Observações livres
[OBSERVACOES]
