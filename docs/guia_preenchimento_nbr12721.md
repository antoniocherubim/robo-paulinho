# Guia interno de preenchimento — ABNT NBR 12721:2006

## 1. Propósito

Este documento orienta o preenchimento **automatizado** da planilha `assets/ABNT_NBR_12721-2006.xlsx`, separando o que cada parte do sistema deve fazer: extração documental, cálculo, fórmula Excel, enriquecimento por LLM e revisão técnica.

- A norma ABNT NBR 12721:2006 (versão corrigida 3, 2021) é usada como **referência local** (PDF na raiz do projeto, não versionado na íntegra).
- Este guia é uma **interpretação operacional** — contém referências a seções e quadros da norma e resumos curtos, nunca transcrições longas (direitos autorais ABNT).
- O guia **não substitui** validação de engenheiro civil. Decisões com impacto técnico/legal estão marcadas como revisão manual.

Complementa a [matriz de responsabilidade por campo](matriz_responsabilidade_campos.md) (`field_responsibility.py`), que é a fonte de verdade programática para permitir/bloquear alterações da LLM.

## 2. Visão geral do fluxo

```mermaid
flowchart LR
  pdfs[PDFs do empreendimento] --> det[Extracao deterministica]
  det --> calc[Calculos e formulas]
  calc --> llm[Enriquecimento LLM controlado]
  llm --> val[Validacao e auditoria]
  val --> rev[Revisao tecnica]
  rev --> xlsx[XLSX final]
```

| Etapa | Módulo principal |
|-------|------------------|
| OCR + pré-filtragem | `documents/pdf_processing.py` |
| Extração determinística | `extraction/deterministic_extraction/` |
| CUB automático e derivados | `orchestration/pipeline_postprocess.py` |
| Extração/enriquecimento LLM | `orchestration/pipeline_llm.py` + `extraction/prompts.py` |
| Validação de completude/semântica | `extraction/validation.py` |
| Preenchimento da planilha | `outputs/excel_writer.py` + `outputs/excel_mapping.py` |
| Auditoria pós-preenchimento | `outputs/excel_audit.py` |
| Comparação determinístico vs LLM | `orchestration/pipeline_compare.py` |

## 3. Mapa dos quadros da planilha

Referências entre parênteses indicam a seção da norma que descreve o quadro.

| Quadro | Finalidade | Fonte principal | Automação possível | Observações |
|--------|------------|-----------------|--------------------|-------------|
| Informações preliminares | Identificação do incorporador, responsável técnico e projeto | Documentos do empreendimento (memorial, alvará) | Alta — extração determinística | Mapeado em `INFO_PRELIMINARES_CELLS`; campos objetivos travados pela matriz |
| Quadro I (5.8.1) | Áreas reais e equivalentes por pavimento e área global (colunas 1–18) | Quadro de áreas do projeto aprovado | Alta para áreas explícitas; totais devem vir de fórmula | Colunas 5, 6, 10, 11, 15–18 são somas — confirmar fórmulas no template |
| Quadro II (5.8.2) | Áreas das unidades autônomas + coeficiente de proporcionalidade (colunas 19–38) | Quadro de áreas do projeto | Alta para áreas privativas; col. 31–36 são cálculo encadeado com o Quadro I | Coeficiente de proporcionalidade (col. 31) = área equiv. não proporcional da unidade / total — candidato a fórmula Excel |
| Quadro III (6.3.2, 6.3.3) | Custo global e unitário de construção (CUB + parcelas adicionais) | CUB do SINDUSCON + estimativas de engenharia | Parcial — CUB automático já implementado; percentuais/adicionais dependem de orçamento | `QUADRO3_CELLS` + `QUADRO3_PERCENTUAIS` no writer; adicionais (fundações, elevadores etc.) exigem dado de engenharia |
| Quadro IV-A (6.3.4–6.3.7) | Custo de construção por unidade + rerrateio de sub-rogação (colunas 39–52) | Quadros I–III + decisão sobre sub-rogação | Baixa — **não implementado no writer** | Sub-rogação (3.12, 3.15) anula/ativa colunas 43–49; revisão manual obrigatória |
| Quadro IV-B (5.8.3) | Resumo das áreas reais para registro/escrituração (colunas A–G) | Derivado dos Quadros I e II | Média — `QUADRO4B_CONFIG` existente | Vagas de garagem mudam de coluna conforme classificação (acessória, comum ou unidade autônoma) |
| Quadro IV-B.1 (5.8.3, nota 1) | Substitui IV-B quando há áreas de terreno de uso exclusivo (casas isoladas/geminadas, incorporação por etapas) | Derivado + projeto | Média — `QUADRO4B1_CONFIG` existente | Decisão IV-B vs IV-B.1 é caso a caso; hoje o writer preenche ambos |
| Quadro V (9.2.2) | Informações gerais (tipo de edificação, pavimentos especiais, numeração, data de aprovação) | Memorial descritivo | Alta — `QUADRO5_CELLS` | `garagens` é derivado de vagas (cálculo); demais campos descritivos |
| Quadro VI (9.2.3) | Memorial descritivo dos equipamentos (instalações elétricas, hidrossanitárias, gás, incêndio, esquadrias etc.) | Memorial descritivo | Média — enriquecimento LLM controlado | `QUADRO6_CONFIG`; conteúdo textual, sem valor numérico-legal direto |
| Quadro VII (9.2.4) | Acabamentos das dependências de uso privativo | Memorial descritivo | Média — LLM controlada | `QUADRO7_CONFIG` |
| Quadro VIII (9.2.5) | Acabamentos das dependências de uso comum | Memorial descritivo | Média — LLM controlada | `QUADRO8_CONFIG` |

## 4. Classificação por tipo de preenchimento

### 4.1 Extração determinística

Campos com evidência objetiva no texto OCR, extraídos por regex/heurística e **travados contra LLM** na matriz:

- CNPJ do incorporador, CREA do responsável.
- Número do alvará, datas de aprovação, cidade/UF.
- Área do terreno, vagas (UA, acessórias, comuns), quantidade de unidades, número de pavimentos.
- Áreas explícitas dos Quadros I e II (privativas cobertas-padrão por pavimento/unidade).

### 4.2 Cálculo (Python)

Valores derivados de outros campos do próprio JSON, sem inventar dado externo:

- Área por pavimento vs área total agrupada — quando o documento traz a área total de N pavimentos idênticos, dividir pelo `qtdPavimentos` (validação de consistência já implementada em `validation.py`).
- Quantidades repetidas — "quantidade" no Quadro I/II é o número de pavimentos/unidades idênticos (5.8.1-s, 5.8.2-u).
- `quadro5.garagens` — derivado de `projeto.vagasComum` + `projeto.vagasAcessorio` (`_preencher_garagens_quadro5`).
- Rateios e áreas equivalentes **somente se** a planilha modelo não tiver fórmula própria (ver 4.3); na dúvida, não calcular em Python.

**Saneamento determinístico (texto/OCR):**

- CNPJ: priorizar ocorrências rotuladas (`CNPJ` na mesma linha), inclusive sem barra entre blocos (`CNPJ10.910.7480001-85`); ignorar sequências numéricas soltas quando houver CNPJ rotulado.
- `projeto.cidadeUf`: extrair o último trecho cidade-UF válido da linha; remover prefixos OCR curtos (`Acd`, `(aga`) sem cortar cidades compostas (`São Paulo`, `Belo Horizonte`, `Foz do Iguaçu`).
- `projeto.nomeEdificio`: preencher **somente** com rótulo explícito (`NOME DO EDIFÍCIO`, `EMPREENDIMENTO`). A tipologia `EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]` **não** é nome comercial do edifício — vai para `quadro3.projetoPadrao.designacao`, não para `nomeEdificio`.
- `incorporador.nome`: remover prefixo OCR lexical genérico (`estar ie que`, tokens curtos) quando houver termo jurídico (LTDA, INCORPORAÇÃO etc.) — sem hardcode de razões sociais específicas.
- Campos textuais: remover prefixo conservador `[arquivo.pdf]` no início; não remover `[RMV]` ou outros colchetes no meio da string.

### 4.3 Fórmula Excel

Campos em que o template já calcula totais ou derivados — o Python deve **apenas alimentar as entradas**:

- Totais de colunas dos Quadros I e II (somas das colunas 5/6/10/11/15–18 e 23/24/28–30/35–38).
- Coeficiente de proporcionalidade (Quadro II, col. 31) e produtos com totais do Quadro I (cols. 32–34), se o template os calcular.
- Percentuais e custo global do Quadro III (custo = área equivalente global × CUB + adicionais).

Inventário completo: [docs/inventario_formulas_xlsx.md](inventario_formulas_xlsx.md) (1301 fórmulas no template). O writer tabular preserva células com fórmula via `celula_tem_formula` em `_escrever_dataframe`. Células fixas do Quadro III ainda não têm guard explícito.

### 4.4 LLM controlada (patch v2)

A LLM **não** preenche a planilha inteira. No modo híbrido (`--comparar-modos`), ela recebe o JSON determinístico pós-processado e devolve apenas um **patch** JSON:

```json
{
  "patch": [
    {
      "path": "projeto.nomeEdificio",
      "valor": "Residencial Exemplo",
      "evidencia": "trecho curto do documento",
      "confianca": "alta"
    }
  ],
  "nao_encontrado": ["quadro7.acabamentos"]
}
```

Campos permitidos (`campos_llm_editaveis()` / `llm_pode_alterar=True`):

- `incorporador.nome`, `responsavel.nome`, `responsavel.endereco`
- `projeto.nomeEdificio`, `projeto.localConstrucao`
- `quadro6.equipamentos`, `quadro7.acabamentos`, `quadro8.acabamentos`

Regras inegociáveis:

- Evidência obrigatória por item; sem evidência clara → `nao_encontrado`, não inventar.
- Campos bloqueados (CNPJ, CREA, unidades, pavimentos, vagas, áreas, CUB, Quadros I/II/V) **não** entram no prompt como editáveis.
- Quadros VI–VIII: lista não vazia com objetos de conteúdo real (template vazio é rejeitado); lista vazia e `evidencia: "template vazio"` são proibidas no patch.
- Patch LLM recebe bloco `EVIDENCIAS QUADROS VI-VIII` com três subseções: `[QUADRO VI - EQUIPAMENTOS]`, `[QUADRO VII - ACABAMENTOS PRIVATIVOS]`, `[QUADRO VIII - ACABAMENTOS AREAS COMUNS]`. Quadro7/8 só podem citar evidências da subseção correspondente; material sem dependência → `nao_encontrado`.
- **Candidatos estruturados** (`CANDIDATOS ESTRUTURADOS QUADROS VII-VIII`) são camada operacional pós-OCR, não inferência de engenharia. Reorganizam dependência + material **somente quando ambos aparecem na mesma linha**. Linha só com `SACADA` ou só com `CIMENTADO` não gera candidato. Quando existir `materiais_contexto` (PISO/PAREDE/TETO), a LLM deve mapear cada material ao campo correto (`pisos`, `paredes`, `tetos`). Evidências brutas permanecem no bloco VI–VIII para contexto; candidatos orientam o patch.
- **Preenchimento determinístico do Quadro VIII:** o extrator preenche `quadro8.acabamentos` automaticamente a partir de candidatos `quadro8` (dependência + material na mesma linha OCR). Material sem superfície explícita vai para `outros`; não infere piso/parede/teto. Quadro VII continua vazio no determinístico até critério privativo separado. **Validação por responsável técnico** antes de uso formal.
- Campos textuais: patch só substitui vazio ou lixo OCR (`,`, `[*.pdf]`, `FICARA CONDIC`).
- O híbrido preserva `qtdUnidades`, `quadro1`, `quadro2`, CUB e derivados do determinístico.

Metadados de debug em `dados_hibrido.json`: `_patch_llm_aplicado`, `_patch_llm_rejeitado` (path + motivo).

Enriquecimento textual típico:

- Nome do edifício/incorporador/responsável quando o OCR vier com lixo (aviso `*.lixo_ocr`).
- Endereço textual limpo (responsável; local da construção).
- Quadros VI, VII e VIII — descrição de equipamentos e acabamentos a partir do memorial.

### 4.5 Revisão manual / engenharia civil

- **ART** — raramente extraível com confiança.
- **Unidades sub-rogadas** (3.12; Quadro IV-A colunas 43–49) — classificação e rerrateio têm efeito legal.
- **Padrão de acabamento** (baixo/normal/alto) — define o projeto-padrão e o CUB aplicável.
- **Critérios de CUB** — escolha entre R1/R8/R16/PIS/CSL e padrão B/N/A (anexo C da norma).
- **Áreas equivalentes e rateios** quando houver ambiguidade — coeficientes de 5.7.3 são faixas (ex.: garagem em subsolo 0,50–0,75), a escolha do valor é decisão de engenharia.

## 5. Campos que exigem validação técnica

| Tema | Risco | Por que precisa validação | Estado atual |
|------|-------|---------------------------|--------------|
| CUB para edifício alto | Alto | Norma define projetos-padrão R8/R16 (anexo C); aplicar R1-N em prédio de 20+ pavimentos distorce o custo | Heurística por pavimentos + aviso semântico (`fallback_baixo_para_predio_alto`) |
| Área equivalente (5.7) | Alto | Coeficientes são faixas (5.7.3) ou cálculo por orçamento (5.7.2); escolha afeta custo global e quotas | Não calculado em Python; colunas `*DifEquiv` aceitas do documento |
| Rateio de áreas comuns (5.8.2; 3.14) | Alto | Coeficiente de proporcionalidade encadeia Quadro II com totais do Quadro I; erro propaga para IV-A e IV-B | Inventariado no XLSX ([inventario_formulas_xlsx.md](inventario_formulas_xlsx.md)); fórmula deve ser preservada; falta auditar/validar o resultado calculado |
| Sub-rogação (3.12; 3.15; 6.3.5–6.3.7) | Alto | Define quotas de rateio e custo suportado por unidade; colunas do IV-A são anuladas/ativadas conforme o caso | Quadro IV-A não implementado; `quadro4a.unidadesSubrogadas` em revisão manual |
| Padrão de acabamento | Alto | Determina o projeto-padrão e o CUB de referência | `projeto.padraoAcabamento` em revisão manual na matriz |
| Quadros VI–VIII | Médio | Conteúdo descritivo arquivado em cartório (art. 32 da Lei 4.591/64); LLM pode alucinar especificações | Enriquecimento LLM permitido, mas sem verificação de evidência documental |
| Área real × privativa × comum × equivalente | Alto | Conceitos distintos na norma (5.2–5.7); confundir real com equivalente invalida os cálculos de custo | Extrator captura áreas explícitas; sem verificação cruzada entre os 4 conceitos |

## 6. Impacto no código atual

| Módulo | Responsabilidade atual | Lacunas |
|--------|------------------------|---------|
| `extraction/deterministic_extraction/` | Regex/heurísticas para campos objetivos, Quadros I/II e Quadro V | Não distingue área real de equivalente; não trata sub-rogação |
| `extraction/field_responsibility.py` | Matriz declarativa origem/edição por campo (cobertura total do schema) | Sem enforcement no pipeline; prompts ainda não a consultam |
| `extraction/validation.py` | Críticos/avisos, consistência área×pavimentos, lixo OCR, templates vazios | Não valida coeficiente de proporcionalidade nem soma de colunas do Quadro I/II |
| `outputs/excel_writer.py` | Preenche Info preliminares, Q1–Q3, Q4-B/B.1, Q5–VIII; protege fórmulas tabulares | Quadro IV-A ausente; células fixas Q3 sem guard de fórmula |
| `outputs/excel_audit.py` | Compara JSON × células preenchidas pós-escrita | Não audita células calculadas por fórmula (valores derivados) |
| `extraction/prompts.py` | Prompt de extração completa (legado) + `PROMPT_ENRIQUECER_PATCH` (patch v2) | Legado ainda gera JSON inteiro; híbrido usa patch controlado |

## 7. Próximas tasks sugeridas

1. ~~**Prompt LLM v2 como patch controlado**~~ — concluído; ver `llm_patch.py`, `gerar_patch_llm`, artefatos `dados_hibrido.json` / `patch_llm.json`.
2. ~~**Inventário de fórmulas no XLSX**~~ — concluído; ver [inventario_formulas_xlsx.md](inventario_formulas_xlsx.md).
3. **Mapear Quadro III com norma + template** — alinhar adicionais 6.3.2-b (fundações, elevadores etc.) com as linhas reais da planilha.
4. **Revisar CUB e padrão do projeto** — validar a heurística por pavimentos contra os projetos-padrão do anexo C, com participação de engenharia.
5. **Enriquecer Quadros VI–VIII com evidência** — exigir trecho-fonte do memorial para cada item gerado pela LLM.

## 8. Perguntas pendentes para validação técnica

- O template XLSX calcula o coeficiente de proporcionalidade (Quadro II, col. 31) e os totais dos Quadros I/II por fórmula, ou espera valores prontos?
- Quais coeficientes de área equivalente (faixas de 5.7.3) o escritório adota como default para garagem em subsolo, terraços e áreas descobertas?
- Quando usar IV-B.1 em vez de IV-B nos empreendimentos típicos do escritório? O writer deve omitir o quadro não utilizado?
- Há casos reais de sub-rogação na carteira atual? Se sim, o Quadro IV-A precisa entrar no roadmap de automação ou permanece manual?
- O padrão de acabamento declarado no memorial pode ser aceito automaticamente ou sempre passa por classificação do engenheiro?
