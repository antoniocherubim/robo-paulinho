# Roadmap — Fundação vetorial para preenchimento NBR 12721

## Norte do projeto

O objetivo final é preencher a planilha ABNT NBR 12721 de forma robusta, rastreável e tecnicamente defensável a partir dos documentos do empreendimento.

A direção estratégica passa a tratar as pranchas arquitetônicas como documentos geométricos, não apenas como texto OCR linear. O texto continua útil, mas deixa de ser a única fonte de verdade para informações que dependem de posição, contorno, área, relação entre ambientes, materiais e elementos desenhados.

Princípio de trabalho: primeiro construir uma representação fiel da prancha; depois detectar ambientes; depois associar textos/materiais; depois calcular; por fim preencher a planilha com evidência.

## Premissas

- OCR linear não preserva relação espacial suficiente para casos como `BWC -> CERÂMICA`.
- PDFs arquitetônicos podem conter linhas, retângulos, curvas e textos com coordenadas extraíveis.
- A planilha ABNT exige campos que dependem de texto, geometria, áreas e interpretação técnica.
- LLM deve ser apoio controlado, não fonte primária para campos calculáveis ou verificáveis por geometria.
- Cada avanço deve produzir evidências auditáveis, preferencialmente com coordenadas, página, PDF de origem e regra aplicada.

## Checklist de acompanhamento

- [x] Task 28 — Inventário vetorial/textual por página.
- [x] Task 29 — Viewer/relatório diagnóstico da geometria.
- [x] Task 30 — Classificação inicial de elementos vetoriais.
- [x] Task 30.1 — Overlay SVG da geometria classificada (ferramenta separada da Task 29).
- [x] Task 31 — Detecção de regiões/células fechadas candidatas a ambientes.
- [x] Task 31.1 — Overlay SVG de regiões candidatas.
- [x] Task 31.2 — Células compostas (regiões maiores por união).
- [ ] Task 32 — Associação espacial texto -> ambiente.
- [ ] Task 33 — Associação espacial material -> ambiente.
- [ ] Task 34 — Calibração de escala e unidades.
- [ ] Task 35 — Cálculo de áreas por ambiente.
- [ ] Task 36 — Agregações por unidade, pavimento e torre.
- [ ] Task 37 — Evidências geométricas estruturadas.
- [ ] Task 38 — Quadro VII por evidência espacial.
- [ ] Task 39 — Quadro VIII por evidência espacial e memorial.
- [ ] Task 40 — Quadros I/II/áreas com validação geométrica.
- [ ] Task 41 — Relatório de rastreabilidade por célula da planilha.
- [ ] Task 42 — Política de confiança e revisão técnica.
- [ ] Task 43 — Suite de regressão com lotes reais.

## Fase 1 — Inventário geométrico confiável

### Task 28 — Inventário vetorial/textual por página

Status: implementada como fundação inicial.

Objetivo: extrair de cada página texto e vetores em JSON diagnóstico, sem tentar preencher a planilha.

Entregáveis esperados:

- Textos com `bbox`, centro e coordenadas normalizadas.
- Linhas com orientação, comprimento, espessura e cor quando disponível.
- Retângulos e curvas com `bbox` e metadados.
- JSON por PDF em `data/output/saida/geometria_pdf/`.
- Testes com prancha tipo real.

Critério de aceite:

- Prancha tipo gera JSON sem OCR.
- `BWC` aparece com coordenadas.
- Linhas/retângulos/curvas aparecem em volume compatível com planta arquitetônica.

## Fase 2 — Normalização e diagnóstico visual

### Task 29 — Viewer/relatório diagnóstico da geometria

Status: implementada.

Objetivo: facilitar inspeção humana do inventário geométrico.

Entregáveis esperados:

- Geração de imagem ou SVG diagnóstico por página.
- Overlay de textos, linhas horizontais/verticais, retângulos e curvas.
- Destaque opcional por tipo de elemento.
- Export em `data/output/saida/geometria_debug/`.

Critério de aceite:

- Abrir uma imagem/SVG da prancha tipo e enxergar onde estão textos e vetores extraídos.
- Confirmar visualmente que coordenadas do JSON batem com a prancha.

### Task 30 — Classificação inicial de elementos vetoriais

Status: implementada (JSON classificado).

Objetivo: separar ruído gráfico de candidatos úteis para paredes, portas, shafts, esquadrias e mobiliário.

Entregáveis esperados:

- Classificação conservadora de linhas por orientação, comprimento, espessura e agrupamento.
- Identificação de segmentos candidatos a parede/contorno (`wall_candidates`).
- Identificação de elementos claramente não estruturais, como carimbo, cotas, hachuras e textos.
- Métricas por página: quantidade de segmentos úteis vs. descartados.
- `classification_reason` por linha e roll-up `axis_aligned_segments` para auditoria.

Critério de aceite:

- Prancha tipo mantém segmentos principais da planta.
- Carimbo e legenda são majoritariamente excluídos da camada de ambiente.

### Task 30.1 — Overlay SVG da geometria classificada

Status: implementada.

Objetivo: viewer SVG separado da Task 29 consumindo `geometria_classificada/*.classificada.json`.

Entregáveis esperados:

- CLI `gerar_debug_classificacao_vetorial` (nao altera `geometry_debug_svg.py`).
- Saida em `geometria_classificada_debug/*.classificada.debug.svg`.
- Cores por bucket: wall_candidates, ruidos, diagonais.
- Tooltips com `classification_reason` e coordenadas.

## Fase 3 — Ambientes como geometria

### Task 31 — Detecção de regiões/células fechadas candidatas a ambientes

Status: implementada (JSON de regiões candidatas, estratégia `adjacent_grid_v1`).

Objetivo: reconstruir possíveis cômodos a partir de paredes/linhas vetoriais.

Entregáveis esperados:

- Normalização e merge de `wall_candidates` horizontais/verticais.
- Células ortogonais fechadas com evidência em `edges` (`source_indices`, `source_count`).
- JSON em `geometria_regioes/*.regioes.json` com stats diagnósticos.
- `detection_strategy: adjacent_grid_v1`; regiões com `confidence: candidate`.

Critério de aceite:

- CLI gera JSON auditável com stats (`grid_cells_checked`, `merged_horizontal`, etc.).
- Testes unitários passam; integração real gera JSON (regiões podem ser zero na v1).
- Associação a ambientes (`BWC`, etc.) permanece na Task 32.

### Task 31.1 — Overlay SVG de regiões candidatas

Status: implementada.

Objetivo: viewer SVG separado consumindo `geometria_regioes/*.regioes.json`.

Entregáveis esperados:

- CLI `gerar_debug_regioes` (nao altera `region_detection.py`).
- Saida em `geometria_regioes_debug/*.regioes.debug.svg`.
- Regioes candidatas e rejeitadas com tooltips (`rejection_reason`, `edge_source_counts`).
- Labels curtos (`r0001`/`x0001`); rejeitadas visiveis por padrao.

### Task 31.2 — Células compostas

Status: concluída. Regiões maiores formadas por união de células fechadas adjacentes.

Entregáveis:

- Módulo `composite_region_detection.py` com estratégia `connected_cell_components_v1`.
- CLI `detectar_regioes_compostas` (não altera `region_detection.py`).
- Saída em `geometria_regioes_compostas/*.regioes_compostas.json`.
- Filtros: dimensões mínimas, `min_fill_ratio`, limites de área/largura/altura vs página.
- Campos por composta: `adjacency_edge_count`, `source_confidences`, `composition_type`,
  `fill_ratio`, `width_ratio`, `height_ratio`.
- Stats: `base_cells`, `pair_checks`, `adjacency_edges`, `duplicate_composites`.
- Dedup por bbox arredondado com `adjacency_tolerance`.

Resultado real TORRE01: 75 `base_cells`, 2775 `pair_checks`, 1 `adjacency_edge`,
74 `components_found`, 0 `composite_regions` aceitas (células isoladas / `single_cell_component`).

### Task 32 — Associação espacial texto -> ambiente

Objetivo: associar rótulos e medidas aos polígonos de ambiente.

Entregáveis esperados:

- Textos internos ao polígono.
- Textos próximos ao centroide ou contorno.
- Regras para rótulo principal (`BWC`, `SALA`, `SACADA`, `CLOSET`, etc.).
- Regras para área textual (`2,70 M2`) versus área calculada.

Critério de aceite:

- `BWC` fica associado ao ambiente correto, não ao material de outro cômodo.
- Área textual do cômodo é vinculada ao mesmo polígono quando estiver visualmente próxima.

### Task 33 — Associação espacial material -> ambiente

Objetivo: resolver o problema central de materiais impressos na planta.

Entregáveis esperados:

- Associação de materiais como `CERÂMICA`, `LAMINADO DE MADEIRA`, `PINTURA`, `PORCELANATO` ao ambiente correto.
- Estratégia para texto quebrado, OCR local ou texto nativo parcial.
- Janela espacial por bbox, não por ordem linear.
- Evidência com PDF, página, bbox do ambiente, bbox do material e distância/regra usada.

Critério de aceite:

- Caso `BWC -> CERÂMICA` é resolvido pela relação espacial.
- `LAMINADO DE MADEIRA` não é atribuído ao BWC se estiver fora da região ou mais próximo de outro ambiente.

## Fase 4 — Medidas e cálculos

### Task 34 — Calibração de escala e unidades

Objetivo: transformar coordenadas PDF em medidas reais quando necessário.

Entregáveis esperados:

- Detecção de escala declarada quando existir.
- Uso de cotas conhecidas como referência quando necessário.
- Registro da escala aplicada por PDF/página.
- Fallback para áreas textuais quando escala não for confiável.

Critério de aceite:

- O sistema sabe quando uma área é calculada por geometria, lida do texto ou indisponível.
- Nenhum cálculo métrico é aplicado sem escala rastreável.

### Task 35 — Cálculo de áreas por ambiente

Objetivo: calcular ou validar áreas de cômodos/regiões.

Entregáveis esperados:

- Área geométrica por polígono.
- Comparação com área textual impressa.
- Alertas para divergências acima de tolerância.
- Fonte preferencial documentada: texto oficial da planta vs. cálculo vetorial.

Critério de aceite:

- Ambientes com área textual têm validação cruzada.
- Ambientes sem área textual podem receber área calculada quando escala for confiável.

### Task 36 — Agregações por unidade, pavimento e torre

Objetivo: transformar ambientes isolados em totais compatíveis com Quadros I, II e áreas do empreendimento.

Entregáveis esperados:

- Agrupamento de ambientes por apartamento/unidade.
- Identificação de repetição por pavimento tipo.
- Regras para torre 01/torre 02 e pavimentos repetidos.
- Consolidação auditável por origem.

Critério de aceite:

- Uma unidade tipo pode ser reconstruída com seus ambientes e áreas.
- Repetição por pavimento é explícita, não hardcoded.

## Fase 5 — Integração com a NBR 12721

### Task 37 — Evidências geométricas estruturadas

Objetivo: criar uma camada intermediária entre geometria e preenchimento da planilha.

Entregáveis esperados:

- JSON de evidências por ambiente.
- Campos: ambiente, tipo privativo/comum, material, área, unidade, pavimento, PDF, página, bbox, regra.
- Separação entre evidência textual, evidência geométrica e evidência OCR local.

Critério de aceite:

- O extrator determinístico consome evidências estruturadas sem depender de texto linear bruto.
- Cada valor relevante tem origem auditável.

### Task 38 — Quadro VII por evidência espacial

Objetivo: preencher acabamentos privativos com base em ambiente + material espacialmente associado.

Entregáveis esperados:

- `quadro7.acabamentos` preenchido a partir de evidências geométricas.
- Tratamento de `BWC`, `Sacada`, `Estar/jantar`, `Closet`, dormitórios e cozinha.
- Material alocado em `pisos`, `paredes`, `tetos` ou `outros` conforme evidência.

Critério de aceite:

- `BWC -> CERÂMICA` passa no lote real.
- Não há associação por ordem linear quando a geometria contradiz.

### Task 39 — Quadro VIII por evidência espacial e memorial

Objetivo: combinar plantas e memorial para acabamentos de áreas comuns.

Entregáveis esperados:

- Ambientes comuns detectados em planta quando possível.
- Memorial continua fonte forte para áreas comuns não desenhadas com detalhe suficiente.
- Conflitos entre planta e memorial são reportados, não resolvidos silenciosamente.

Critério de aceite:

- Hall, escada, circulação, barrilete e áreas técnicas têm origem de evidência clara.

### Task 40 — Quadros I/II/áreas com validação geométrica

Objetivo: usar geometria para validar ou completar áreas e unidades.

Entregáveis esperados:

- Comparação entre áreas declaradas em quadros/cálculos e áreas inferidas.
- Alertas para divergências.
- Regras para aceitar texto oficial quando geometria estiver incompleta.

Critério de aceite:

- O sistema não apenas preenche, mas aponta inconsistências relevantes.

## Fase 6 — Auditoria e robustez

### Task 41 — Relatório de rastreabilidade por célula da planilha

Objetivo: cada campo preenchido deve ter justificativa verificável.

Entregáveis esperados:

- Para cada campo/célula relevante: valor, fonte, PDF, página, evidência e regra.
- Export JSON e relatório legível.
- Marcação de campos calculados, inferidos, lidos e pendentes.

Critério de aceite:

- Um revisor consegue entender por que a planilha recebeu cada valor.

### Task 42 — Política de confiança e revisão técnica

Objetivo: classificar resultados por nível de confiança.

Entregáveis esperados:

- Níveis: alto, médio, baixo, pendente.
- Critérios objetivos por tipo de campo.
- Bloqueio ou aviso para campos críticos sem evidência suficiente.

Critério de aceite:

- Planilha final diferencia dado sólido de dado que precisa revisão humana.

### Task 43 — Suite de regressão com lotes reais

Objetivo: proteger o aprendizado acumulado.

Entregáveis esperados:

- Fixtures controladas de PDFs reais ou recortes permitidos.
- Casos de BWC/cerâmica, sacada/laminado, hall/elevador, elevadores, gás, áreas.
- Testes de não regressão por evidência, não apenas por valor final.

Critério de aceite:

- Uma mudança em geometria ou OCR não degrada silenciosamente os casos já conhecidos.

## Ordem recomendada imediata

1. Task 29 — gerar visualização/overlay do inventário.
2. Task 30 — classificar vetores úteis e remover ruído de carimbo/legenda.
3. Task 31 — começar a detectar regiões candidatas a ambientes.
4. Task 32 — associar textos aos ambientes.
5. Task 33 — resolver materiais por proximidade/região, incluindo `BWC -> CERÂMICA`.

## Fora de escopo por enquanto

- Preencher novos campos da planilha diretamente a partir do inventário bruto.
- Usar LLM para adivinhar materiais não associados geometricamente.
- Calcular áreas reais sem escala confiável.
- Reescrever o pipeline atual antes de a camada geométrica provar valor em lote real.

## Definição de pronto para a virada geométrica

A abordagem geométrica estará pronta para substituir heurísticas frágeis quando:

- Ambientes principais forem detectados na prancha tipo com taxa aceitável.
- Textos e materiais forem associados por coordenada, não por ordem linear.
- Áreas tiverem fonte clara: texto, cálculo ou indisponível.
- O preenchimento dos Quadros VII/VIII puder apontar evidência espacial.
- O relatório final permitir revisão técnica sem depender de confiança cega no sistema.
