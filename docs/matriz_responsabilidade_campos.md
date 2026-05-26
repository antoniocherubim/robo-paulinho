# Matriz de responsabilidade por campo

Documenta quem é responsável por cada campo do JSON/planilha NBR 12721:2006: extrator determinístico, cálculo interno, fórmula Excel, LLM ou revisão manual. A matriz guia os próximos prompts e impede que a LLM sobrescreva campos objetivos.

**Fonte de verdade (código):** [`src/nbr12721/extraction/field_responsibility.py`](../src/nbr12721/extraction/field_responsibility.py)

| Origem | Significado |
|--------|-------------|
| `deterministico` | Extraído por regex/OCR/heurísticas do extrator |
| `calculo` | Derivado no pós-processamento (ex.: garagens a partir de vagas) |
| `formula_excel` | Preferir fórmulas/células do template quando existirem |
| `llm` | Enriquecimento textual descritivo permitido |
| `revisao_manual` | Sem evidência objetiva confiável; conferir com engenharia |

## Tabela de campos

| Campo | Origem | LLM pode alterar? | Status | Risco | Observação |
|-------|--------|-------------------|--------|-------|------------|
| incorporador.nome | deterministico | Sim | implementado | medio | Razão social; LLM apenas se vazio ou lixo OCR |
| incorporador.cnpj | deterministico | Não | implementado | alto | CNPJ por regex/OCR; não inferir |
| incorporador.endereco | deterministico | Não | implementado | medio | Exige evidência documental |
| responsavel.nome | deterministico | Sim | implementado | medio | LLM apenas se vazio ou lixo OCR |
| responsavel.crea | deterministico | Não | implementado | alto | Padrão CREA objetivo |
| responsavel.art | revisao_manual | Não | planejado | alto | Conferência manual |
| responsavel.endereco | deterministico | Sim | implementado | medio | LLM apenas se vazio ou lixo OCR |
| projeto.nomeEdificio | deterministico | Sim | implementado | medio | LLM apenas se vazio ou lixo OCR |
| projeto.localConstrucao | deterministico | Sim | implementado | alto | LLM apenas se vazio ou lixo OCR |
| projeto.cidadeUf | deterministico | Não | implementado | alto | Município/UF (ex.: Curitiba-PR) |
| projeto.qtdUnidades | deterministico | Não | implementado | alto | Total de unidades (áreas × quantidade) |
| projeto.numPavimentos | deterministico | Não | implementado | alto | Número de pavimentos |
| projeto.vagasUA | deterministico | Não | implementado | medio | Vagas por unidade autônoma |
| projeto.vagasAcessorio | deterministico | Não | implementado | medio | Vagas acessórias/duplas |
| projeto.vagasComum | deterministico | Não | implementado | medio | Vagas comuns |
| projeto.areaTerreno | deterministico | Não | implementado | alto | Área do terreno (m²) |
| projeto.dataAprovacao | deterministico | Não | implementado | alto | Data de aprovação |
| projeto.numAlvara | deterministico | Não | implementado | alto | Número do alvará |
| projeto.padraoAcabamento | revisao_manual | Não | planejado | alto | Padrão de acabamento; impacto técnico e custo |
| projeto.projetoPadrao.R | deterministico | Não | implementado | alto | Marcação padrão residencial |
| projeto.projetoPadrao.CS | deterministico | Não | implementado | alto | Marcação comercial/serviços |
| projeto.projetoPadrao.CL | deterministico | Não | implementado | alto | Marcação comercial leve |
| projeto.projetoPadrao.CG | deterministico | Não | implementado | alto | Marcação comercial geral |
| projeto.projetoPadrao.CP | deterministico | Não | implementado | alto | Marcação comercial pesado |
| projeto.projetoPadrao.CP1Q | deterministico | Não | implementado | alto | Marcação comercial pesado 1Q |
| quadro1.pavimentos | deterministico | Não | implementado | alto | Quadro I — pavimentos e áreas |
| quadro2.unidades | deterministico | Não | implementado | alto | Quadro II — unidades e áreas |
| quadro3.valorCub | deterministico | Não | implementado | alto | CUB (SINDUSCON + regra por pavimentos) |
| quadro3.sindicato | deterministico | Não | implementado | alto | Sindicato/fonte do CUB (SINDUSCON) |
| quadro3.mesCub | deterministico | Não | implementado | alto | Mês/ano de referência do CUB |
| quadro3.projetoPadrao.* | deterministico | Não | parcial | alto | Linha projeto-padrão do Quadro III (designacao, padrao, areaEquiv, quartos, etc.) |
| quadro3.percentuais_e_adicionais | formula_excel | Não | parcial | alto | percMateriais, percMaoObra, adicionais 6.3–6.6, rateios |
| quadro4a.unidadesSubrogadas | revisao_manual | Não | planejado | alto | Conferência documental |
| quadro5.garagens | calculo | Não | implementado | medio | Derivado de vagasComum/vagasAcessorio |
| quadro5.* | deterministico | Não | implementado | medio | Demais campos do Quadro V (tipo, numeração, etc.) |
| quadro6.equipamentos | llm | Sim | implementado | medio | Quadro VI — equipamentos |
| quadro7.acabamentos | llm | Sim | implementado | medio | Quadro VII — acabamentos internos |
| quadro8.acabamentos | llm | Sim | implementado | medio | Quadro VIII — áreas comuns |

O path `quadro5.*` cobre, entre outros: `tipoEdificacao`, `numPavimentos`, `unidadesPorPav`, `numeracao`, `pilotis`, `transicao`, `pavComunitarios`, `outrosPav`, `dataAprovacao`, `outrasIndicacoes`. A entrada explícita `quadro5.garagens` tem precedência (origem `calculo`).

O path `quadro3.projetoPadrao.*` cobre: `designacao`, `padrao`, `numPav`, `areaEquiv`, `quartos`, `salas`, `banheiros`, `quartosEmp`.

Agregado formal `quadro3.percentuais_e_adicionais` cobre as folhas numéricas de percentuais/adicionais listadas abaixo (verificadas por teste contra o schema).

Subcampos agregados em `quadro3.percentuais_e_adicionais`: `percMateriais`, `percMaoObra`, `fundacoes`, `elevadores`, `fogoes`, `aquecedores`, `bombasRecalque`, `incineracao`, `arCondicionado`, `calefacao`, `ventilacao`, `outros6_3`, `playground`, `urbanizacao`, `recreacao`, `ajardinamento`, `instCondominio`, `outros6_5`, `outros6_6`, `impostos`, `projArq`, `projEstrut`, `projInst`, `projEsp`, `percConstrutor`, `percIncorporador`.

Colunas de área equivalente (`areaPrivCobDifEquiv`, `areaComumNPCobDifEquiv`, etc.) nos quadros I e II seguem a planilha modelo quando há fórmula Excel; não devem ser inventadas pela LLM.

---

## Decisões que exigem validação de engenharia civil

- **responsavel.art** — ART raramente aparece de forma confiável no OCR.
- **quadro4a.unidadesSubrogadas** — sub-rogação exige conferência documental.
- **projeto.projetoPadrao.*** — classificação R/CS/CL/CG/CP/CP1Q impacta CUB e custos.
- **quadro1.pavimentos** / **quadro2.unidades** — inconsistências área × quantidade (validação semântica).
- **quadro3.valorCub** — escolha do tipo CUB em edifícios altos (R16-N vs R1-N) quando indisponível na tabela.
- **projeto.padraoAcabamento** — classificação de acabamento com impacto em custo e memorial.
- Conteúdo dos quadros VI–VIII após enriquecimento LLM.
- **quadro3.projetoPadrao.*** — conferência da linha de projeto-padrão no Quadro III.

---

## Campos que dependem de cálculo ou fórmula

- **quadro5.garagens** — texto montado a partir de `projeto.vagasComum` e `projeto.vagasAcessorio` no pós-processamento.
- **quadro3.percentuais_e_adicionais** — percentuais e adicionais do Quadro III; preferir células/fórmulas do template (`QUADRO3_PERCENTUAIS` no writer).
- **Áreas equivalentes** — colunas `*DifEquiv` nos quadros I e II quando a planilha já calcula totais e rateios.

---

## Campos permitidos para enriquecimento por LLM

**Condicional (apenas se vazio ou lixo OCR):**

- incorporador.nome
- responsavel.nome
- responsavel.endereco
- projeto.nomeEdificio
- projeto.localConstrucao

**Livre (origem LLM):**

- quadro6.equipamentos
- quadro7.acabamentos
- quadro8.acabamentos

Consulte `llm_pode_alterar(path)`, `path_coberto_pela_matriz(path)`, `origem_do_campo(path)` e `campos_llm_editaveis()` no módulo Python antes de integrar restrições no pipeline ou nos prompts.

O teste `test_matriz_cobre_todas_folhas_do_schema` garante que cada folha do esqueleto canônico (`schema._esqueleto_vazio`) está coberta por entrada exata, wildcard (`.*`) ou agregado em `PATHS_AGREGADOS`.
