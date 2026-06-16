# NBR 12721:2006 — Preenchimento automático

Extrai dados de PDFs de incorporação imobiliária e preenche a planilha ABNT NBR 12721:2006 com apoio de LLM (Anthropic/Claude ou OpenAI).

## Estrutura do projeto

```
paulo/
├── src/nbr12721/          # codigo-fonte (pacote Python)
├── tests/
├── docs/
├── assets/
│   └── ABNT_NBR_12721-2006.xlsx
├── data/
│   ├── input/documentos/  # PDFs de entrada
│   └── output/saida/      # artefatos gerados
├── tasks/
├── logs/                  # arquivos .log (gerados em runtime)
├── .env.example
├── main.py                # entrypoint simples para debug/execucao
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Início rápido

1. Coloque os PDFs em `data/input/documentos/`.
2. A planilha modelo fica em `assets/ABNT_NBR_12721-2006.xlsx`.
3. Configure o LLM: `cp .env.example .env` e preencha as chaves.
4. Se for processar PDF rasterizado/escaneado, instale Tesseract + Poppler.
5. Instale e execute:

```bash
pip install -r requirements.txt
pip install -e .
python3 main.py
```

Reutilizar texto já extraído (pula leitura de PDFs):

```bash
python3 main.py --skip-extracao
```

### Inventario geometrico de pranchas

A fundacao vetorial/textual fica separada do pipeline principal. Ela gera JSONs
diagnosticos com textos, linhas, retangulos e curvas por pagina, preservando
coordenadas em pontos PDF (`pdfplumber_top_left_points`). Por padrao, processa
apenas pranchas tipo (`PLA-TIPO`/`TIPO_TORRE`).

```bash
PYTHONPATH=src ./venv/bin/python -m nbr12721.tools.inventariar_geometria_pdfs --max-paginas 1
```

Saida padrao: `data/output/saida/geometria_pdf/*.geometria.json`.

Usar o texto filtrado em cache **sem refiltrar** (mesmo conteúdo de `textos_filtrados.txt` gerado no OCR original). **Após mudanças no prefiltro**, regenere o cache com pipeline completo (OCR) antes de usar `--usar-texto-filtrado-cache` — o flag não refiltra automaticamente.

```bash
python3 main.py --usar-texto-filtrado-cache
```

### Comparação determinístico vs LLM

Compare os dois modos de extração no **mesmo** `textos_filtrados.txt`, sem re-OCR e **sem** sobrescrever `dados_extraidos.json`, a planilha principal nem `validacao_dados.json`. Artefatos ficam em `data/output/saida/comparacao/`.

O fluxo híbrido (LLM v2) parte do JSON **determinístico já pós-processado** (CUB, derivados seguros, `quadro5.garagens`) e aplica apenas um **patch controlado** nos campos permitidos pela matriz (`llm_pode_alterar`). A LLM não gera JSON inteiro: devolve `patch` + `evidencia` por item. Falha da LLM no modo comparação é **não bloqueante** (`patch: []`, `nao_encontrado: ["llm_indisponivel"]`).

```bash
# 1) Gerar textos_filtrados.txt uma vez (pipeline normal com OCR)
PYTHONPATH=src ./venv/bin/python main.py --deterministico --json-only

# 2) Comparar modos no mesmo texto cacheado
PYTHONPATH=src ./venv/bin/python main.py --comparar-modos --usar-texto-filtrado-cache
```

Artefatos em `comparacao/`:

| Arquivo | Descrição |
|---------|-----------|
| `dados_deterministico.json` | Extração determinística + pós-processamento |
| `dados_hibrido.json` | Determinístico + patch LLM aplicado |
| `validacao_hibrido.json` | Validação do híbrido |
| `patch_llm.json` | Patch bruto (`patch`, `nao_encontrado`) |
| `dados_llm.json` | Modo legado (JSON inteiro via LLM), opcional |
| `comparacao_modos.json` | Relatório com seções `llm` e `hibrido` |

O relatório lista `melhorias_llm` / `regressoes_llm` (legado) e, para o híbrido, `hibrido.melhorias` / `hibrido.regressoes` comparados sempre contra o determinístico. Remoção de aviso semântico **não** conta como melhoria se houve perda de dado estrutural (`qtdUnidades`, Quadros I–II, CUB, garagens etc.). A decisão final entre modos é de revisão humana/engenharia, não automática.

Artefatos gerados em `data/output/saida/` (`NBR_12721_preenchida.xlsx`, `dados_extraidos.json`, etc.).

### Logs

O pipeline grava logs estruturados em **console e arquivo**:

| Variável | Default | Descrição |
|----------|---------|-----------|
| `PASTA_LOGS` | `logs` | Pasta dos arquivos `.log` (relativa à raiz do projeto) |
| `LOG_ARQUIVO` | `nbr12721.log` | Nome base; cada execucao gera `nome_YYYYMMDD_HHMMSS.log` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Exemplo de linha no arquivo:

```
2026-05-20 14:30:01 | INFO     | nbr12721.orchestration.pipeline | 3 PDF(s) | Extraindo texto...
```

O arquivo usa rotação automática (5 MB, até 5 backups). Logs ficam em `logs/` (ignorados pelo git, exceto `.gitkeep`).

Alternativa sem `pip install -e .`:

```bash
python3 main.py
```

Alternativa via pacote:

```bash
python3 -m nbr12721
```

Se o pacote estiver instalado com `pip install -e .`, tambem da para rodar:

```bash
nbr12721
```

### Migração do layout antigo

Se você usava `documentos/` e `saida/` na raiz:

```env
PASTA_DOCS=data/input/documentos
PASTA_SAIDA=data/output/saida
PLANILHA=assets/ABNT_NBR_12721-2006.xlsx
```

Mova os PDFs para `data/input/documentos/` e a planilha modelo para `assets/`.

---

## Configurar o LLM

O pipeline chama apenas `chamar_llm()` — você escolhe o backend via variáveis de ambiente, **sem alterar código**.

### `LLM_PROVIDER` — qual backend usar

| Valor | Quando usar | O que é tentado |
|-------|-------------|-----------------|
| `anthropic` | **Default.** Claude/Anthropic (API, SDK ou CLI) | API → Agent SDK → CLI |
| `openai` | Conta/custo OpenAI; sem misturar com Claude | Somente OpenAI API |
| `auto` | Máxima chance de sucesso com duas contas | Cadeia completa do primário, depois do secundário |

- Se `LLM_PROVIDER` estiver **ausente**, equivale a `anthropic` (retrocompatível).
- Valor inválido → aviso no log e fallback para `anthropic`.

### `LLM_AUTO_PRIMARY` — ordem no modo `auto`

Só importa quando `LLM_PROVIDER=auto` e **ambos** os providers estão disponíveis (chaves/credenciais).

| Valor | Ordem |
|-------|-------|
| `anthropic` (default) | Anthropic (API→SDK→CLI), depois OpenAI API |
| `openai` | OpenAI API, depois Anthropic (API→SDK→CLI) |

Detalhes de fallback: [docs/llm-fallback-policy.md](docs/llm-fallback-policy.md).  
Seleção de provider: [docs/llm-provider-strategy.md](docs/llm-provider-strategy.md).

A **matriz de responsabilidade por campo** ([docs/matriz_responsabilidade_campos.md](docs/matriz_responsabilidade_campos.md), código em `src/nbr12721/extraction/field_responsibility.py`) define quais paths a LLM poderá alterar nas próximas tasks (CNPJ, quantidades e quadros I/II permanecem bloqueados). Hoje é referência e documentação — o pipeline ainda não aplica `llm_pode_alterar()` automaticamente.

---

## Exemplos de `.env`

Copie o template: `cp .env.example .env` e use **um** dos cenários (ou combine `auto`).

### 1. Anthropic API

```env
LLM_PROVIDER=anthropic
PASTA_DOCS=data/input/documentos
PASTA_SAIDA=data/output/saida
PLANILHA=assets/ABNT_NBR_12721-2006.xlsx

ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### 2. OpenAI API

```env
LLM_PROVIDER=openai

OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
```

### 3. Claude CLI (sem API key)

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=
```

```bash
npm install -g @anthropic-ai/claude-code
claude
```

### 4. Modo `auto`

```env
LLM_PROVIDER=auto
LLM_AUTO_PRIMARY=anthropic

ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

---

## Outras variáveis

| Variável | Descrição |
|----------|-----------|
| `PASTA_DOCS` | PDFs de entrada (default: `data/input/documentos`) |
| `PASTA_SAIDA` | Saída (default: `data/output/saida`) |
| `PLANILHA` | Planilha modelo (default: `assets/ABNT_NBR_12721-2006.xlsx`) |
| `TESSERACT_CMD` | Caminho do executável do Tesseract; deixe vazio se `tesseract` estiver no `PATH` |
| `TESSERACT_LANG` | Idiomas do OCR (default: `por+eng`) |
| `POPPLER_PATH` | Pasta do Poppler/`pdftoppm`; útil no Windows quando não estiver no `PATH` |
| `OCR_DPI` | Resolução usada ao rasterizar páginas para OCR (default: `150`; menor usa menos RAM) |
| `OCR_MIN_CHARS_PAGINA` | Mínimo de caracteres nativos por página para pular OCR (default: `80`) |
| `OCR_USAR_ARQUIVOS_TEMP` | Usa arquivos temporários no OCR em vez de manter imagens na RAM (default: `true`) |
| `OCR_GRAYSCALE` | Rasteriza páginas em escala de cinza para reduzir memória (default: `true`) |
| `OCR_TIMEOUT_SEGUNDOS` | Tempo máximo por página no Tesseract (default: `120`) |
| `OCR_MAX_IMAGE_PIXELS` | Limite de pixels aceito pelo PIL no fallback em memória (default: `120000000`) |
| `LIMITE_CHARS_TEXTO_FILTRADO` | Limite do texto enviado aos lotes da LLM apos filtro de OCR/PDF (default: `16000`) |
| `CLAUDE_EXECUTABLE` | Caminho absoluto do `claude`, se não estiver no PATH |
| `CLAUDE_EXTRA_PATHS` | Diretórios extras no PATH |
| `CLAUDE_CANDIDATE_PATHS` | Caminhos candidatos ao executável CLI |

Paths relativos no `.env` resolvem a partir da **raiz do projeto**, não do diretório atual.

## Decisões técnicas a validar

Esta seção registra critérios automáticos que podem depender de interpretação técnica
ou validação por engenheiro civil. Eles devem ser revisados antes de tratar a planilha
como versão final para uso profissional.

### CUB residencial por número de pavimentos

Critério provisório: quando o projeto for residencial (`projeto.projetoPadrao.R=true`)
e o CUB do Sinduscon vier no formato residencial por padrão baixo/normal/alto, o sistema
seleciona automaticamente o padrão normal mais compatível com o porte do edifício.

Regra proposta para validação:

| Condição | Tipo CUB preferido | Fallbacks |
|----------|--------------------|-----------|
| Residencial com `numPavimentos >= 8` | `R16-N` | `R8-N`, `R1-N`, `R4-N` |
| Residencial com menos de 8 pavimentos | `R8-N` ou `R1-N` conforme disponibilidade | `R4-N` |

Motivo: no conjunto de PDFs atual o empreendimento é residencial multifamiliar vertical,
com cerca de 21 pavimentos e 320 unidades. O PDF CUB atual do Sinduscon Norte PR apresenta
tipologias residenciais como `R-1`, `R-8` e `R-16` em colunas de padrão baixo, normal e alto,
em vez de chaves antigas como `R4-N`.

Status: **a validar com engenheiro civil**. A seleção automática é pragmática para viabilizar
o preenchimento mínimo, mas pode precisar ser ajustada conforme enquadramento normativo,
características do empreendimento ou orientação profissional.

### Saneamento textual pós-OCR

O sistema remove apenas ruídos formais de OCR em campos textuais (identificação, local da
obra, nomes e endereços de responsável/incorporador), como símbolos isolados, vírgulas finais
e tokens finais curtos sem significado após separadores.

A limpeza **não corrige** endereço, nomes nem dados técnicos de engenharia; ela não infere
nem normaliza conteúdo semântico, apenas descarta lixo formal reconhecível do OCR.

Campos técnicos como áreas, pavimentos, vagas, CNPJ, CREA, alvará e datas **não** passam
por essa regra textual.

Decisão classificada como **operacional/OCR**, não como critério técnico de engenharia civil.

### Agrupamento de pavimentos repetidos no Quadro I

O sistema agrupa pavimentos tipo idênticos em uma única linha do Quadro I.
A área lançada na linha representa **um pavimento tipo individual**.
A coluna `qtdPavimentos` representa quantas vezes esse pavimento se repete.
Isso segue a lógica da própria planilha, que totaliza áreas com multiplicação por
quantidade de pavimentos (`SUMPRODUCT`).
A regra evita duplicação de área quando o texto OCR informa uma soma total dos
pavimentos tipo.

Status: **a validar com engenheiro civil**, especialmente quando houver torres,
pavimentos tipo não idênticos ou áreas comuns distribuídas por pavimento.

### Validação semântica não bloqueante

Além da completude estrutural, o sistema sinaliza campos que parecem lixo OCR ou
templates vazios nos Quadros VI, VII e VIII.
O **Quadro VI** possui preenchimento determinístico conservador para equipamentos
explicitamente citados no OCR (elevadores, bombas, reservatórios, gás etc.).
Campos `tipo` e `acabamento` permanecem vazios sem evidência explícita.
O **Quadro VII** possui preenchimento determinístico parcial para acabamentos
privativos quando dependência e material aparecem explicitamente na mesma linha OCR
ou em janela curta de duas linhas consecutivas (dependência + material na linha
seguinte), incluindo materiais colados como `LAMINADODEMADEIRA`. Materiais sem
`PISO`/`PAREDE`/`TETO` vão para `outros`. Cobertura parcial — revisão técnica
obrigatória; casos OCR mais complexos continuam dependentes de LLM ou revisão manual.
Como a ordem textual de plantas não preserva a geometria, `BWC` e `BANHO` só
recebem acabamento quando o material aparece explicitamente na mesma linha.
Associações por janela curta seguem evidência OCR, não plausibilidade de engenharia
(ex.: `BWC` + laminado na linha seguinte pode exigir correção manual na planilha).
A LLM continua podendo auxiliar no enriquecimento textual, mas não deve inventar
equipamentos sem evidência.
Esses avisos **não impedem** o preenchimento da planilha por padrão.
Eles servem para revisão humana antes de considerar a planilha final confiável.
CUB incompatível com o porte do empreendimento também entra como aviso semântico,
especialmente quando o tipo ideal (R16-N / R8-N) não está disponível na fonte parseada.

Status: **operacional**, com impacto técnico indireto; deve ser revisado por responsável técnico.

### Escrita da planilha com arquitetura híbrida

O sistema usa **pandas** para montar DataFrames intermediários dos quadros tabulares.
O sistema mantém **openpyxl** para escrever no template Excel original, preservando
fórmulas, células mescladas, estilos e referências entre abas.
A troca completa por `pandas.to_excel()` não é adequada, pois recriaria o layout.
Alterações futuras na planilha base devem ser feitas preferencialmente em
`excel_mapping.py` (células fixas) e `excel_tables.py` (regras de dados).

### Auditoria pós-preenchimento

Após gerar o XLSX, o pipeline pode comparar `dados_extraidos.json` com as células
efetivamente preenchidas e salvar `data/output/saida/auditoria_planilha.json`.
Isso valida o **mapeamento técnico JSON → planilha**; não substitui revisão de
engenharia civil, mas ajuda a detectar erro de célula, linha ou desalinhamento com o template.
A auditoria é **não bloqueante** (falhas são registradas em log e no campo `erro` do relatório).
Controle: `AUDITORIA_PLANILHA=true` no `.env` (padrão).

## OCR com Tesseract

Se o PDF nao tiver texto nativo, o pipeline tenta OCR com `pytesseract` + `pdf2image`.
Nesse fluxo, o projeto usa:

- `Tesseract` para reconhecer o texto nas imagens
- `Poppler` para converter o PDF em imagens antes do OCR

O caminho do executavel do Tesseract deve vir do `.env`, nunca hardcoded no codigo.

### Instalar dependencias do OCR

Linux (Ubuntu/Debian):

```bash
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-por tesseract-ocr-eng poppler-utils
```

Depois confira:

```bash
which tesseract
tesseract --version
tesseract --list-langs
which pdftoppm
```

Windows:

1. Instale o Tesseract OCR.
2. Instale o Poppler for Windows.
3. Preencha `TESSERACT_CMD` e `POPPLER_PATH` no `.env`.

Exemplo de `.env`:

```env
TESSERACT_CMD=
TESSERACT_LANG=por+eng
OCR_DPI=150
OCR_MIN_CHARS_PAGINA=80
OCR_USAR_ARQUIVOS_TEMP=true
OCR_GRAYSCALE=true
OCR_TIMEOUT_SEGUNDOS=120
OCR_MAX_IMAGE_PIXELS=120000000
LIMITE_CHARS_TEXTO_FILTRADO=16000
POPPLER_PATH=
```

- Linux/macOS: normalmente `TESSERACT_CMD` e `POPPLER_PATH` podem ficar vazios se `tesseract` e `pdftoppm` estiverem no `PATH`.
- Windows: geralmente voce vai preencher `TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe` e `POPPLER_PATH=C:\poppler\Library\bin`.
- Linux: se preferir explicitar o executavel, um valor comum para `TESSERACT_CMD` e `/usr/bin/tesseract`.

Exemplo Linux com path explicito:

```env
TESSERACT_CMD=/usr/bin/tesseract
TESSERACT_LANG=por+eng
OCR_DPI=150
OCR_MIN_CHARS_PAGINA=80
OCR_USAR_ARQUIVOS_TEMP=true
OCR_GRAYSCALE=true
OCR_TIMEOUT_SEGUNDOS=120
OCR_MAX_IMAGE_PIXELS=120000000
LIMITE_CHARS_TEXTO_FILTRADO=16000
POPPLER_PATH=
```

Exemplo Windows:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANG=por+eng
OCR_DPI=150
OCR_MIN_CHARS_PAGINA=80
OCR_USAR_ARQUIVOS_TEMP=true
OCR_GRAYSCALE=true
OCR_TIMEOUT_SEGUNDOS=120
OCR_MAX_IMAGE_PIXELS=120000000
LIMITE_CHARS_TEXTO_FILTRADO=16000
POPPLER_PATH=C:\poppler\Library\bin
```

Para reduzir uso de RAM no OCR, o pipeline processa 1 PDF por vez e 1 página por vez.
Por padrão, cada página rasterizada vai para arquivo temporário e o Tesseract lê o caminho
do arquivo, evitando manter a imagem dentro do processo Python. Se ainda ficar pesado,
reduza `OCR_DPI` para `120`.

---

## Documentação técnica

| Documento | Conteúdo |
|-----------|----------|
| [docs/inventario_formulas_xlsx.md](docs/inventario_formulas_xlsx.md) | Inventário de fórmulas do template XLSX |
| [docs/guia_preenchimento_nbr12721.md](docs/guia_preenchimento_nbr12721.md) | Guia operacional de preenchimento baseado na NBR 12721 |
| [docs/matriz_responsabilidade_campos.md](docs/matriz_responsabilidade_campos.md) | Origem por campo (determinístico, LLM, cálculo, etc.) |
| [docs/llm-provider-strategy.md](docs/llm-provider-strategy.md) | `LLM_PROVIDER`, modos |
| [docs/llm-fallback-policy.md](docs/llm-fallback-policy.md) | Ordem de tentativas em falha |
| [docs/llm-response-contract.md](docs/llm-response-contract.md) | Formato `str \| None` |

A norma ABNT NBR 12721:2006 é usada apenas como **referência local** (PDF na raiz, não versionado na íntegra por direitos autorais). O guia de preenchimento é interpretação operacional e **não substitui validação de engenheiro civil**.

O writer preserva fórmulas existentes em células tabulares (Quadros I, II, IV-B, IV-B.1, VI–VIII): células cujo valor começa com `=` não são sobrescritas. Ver [docs/inventario_formulas_xlsx.md](docs/inventario_formulas_xlsx.md).

---

## Módulos (`src/nbr12721/`)

| Módulo | Responsabilidade |
|--------|------------------|
| `main.py` | Entrypoint unico para debug/execucao direta |
| `logging_setup.py` | Console + arquivo `logs/*.log` (rotação) |
| `pipeline.py` | Orquestração do fluxo |
| `config.py` | Paths, limites, resolvers de provider/modelo |
| `field_responsibility.py` | Matriz origem/edição por campo (restrição LLM futura) |
| `prompts.py` | Prompts LLM |
| `llm.py` | Cliente multi-provider (`chamar_llm`) |
| `pdf_processing.py` | Extração PDF, OCR, pré-filtragem |
| `serialization.py` | Parse JSON e compactação de resumos |
| `cub.py` | Coleta e formatação de dados CUB |
| `excel_tables.py` | DataFrames intermediários por quadro |
| `excel_mapping.py` | Mapeamento JSON → células do template |
| `excel_writer.py` | Orquestração do preenchimento (pandas + openpyxl) |
| `excel_formula_inventory.py` | Inventário de fórmulas do template; proteção tabular |
| `excel_audit.py` | Auditoria JSON vs células do XLSX preenchido |
| `formatacao.py` | Formatação BRL |

---

## Testes

```bash
pip install -e .   # opcional
./run_tests.sh
# ou: PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Mapa da suite: [tests/README.md](tests/README.md).
