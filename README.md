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

Artefatos gerados em `data/output/saida/` (`NBR_12721_preenchida.xlsx`, `dados_extraidos.json`, etc.).

### Logs

O pipeline grava logs estruturados em **console e arquivo**:

| Variável | Default | Descrição |
|----------|---------|-----------|
| `PASTA_LOGS` | `logs` | Pasta dos arquivos `.log` (relativa à raiz do projeto) |
| `LOG_ARQUIVO` | `nbr12721.log` | Nome do arquivo de log |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Exemplo de linha no arquivo:

```
2026-05-20 14:30:01 | INFO     | nbr12721.pipeline | 3 PDF(s) | Extraindo texto...
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
| `LIMITE_CHARS_TEXTO_FILTRADO` | Limite do texto enviado aos lotes da LLM apos filtro de OCR/PDF (default: `16000`) |
| `CLAUDE_EXECUTABLE` | Caminho absoluto do `claude`, se não estiver no PATH |
| `CLAUDE_EXTRA_PATHS` | Diretórios extras no PATH |
| `CLAUDE_CANDIDATE_PATHS` | Caminhos candidatos ao executável CLI |

Paths relativos no `.env` resolvem a partir da **raiz do projeto**, não do diretório atual.

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
LIMITE_CHARS_TEXTO_FILTRADO=16000
POPPLER_PATH=
```

Exemplo Windows:

```env
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
TESSERACT_LANG=por+eng
LIMITE_CHARS_TEXTO_FILTRADO=16000
POPPLER_PATH=C:\poppler\Library\bin
```

---

## Documentação técnica

| Documento | Conteúdo |
|-----------|----------|
| [docs/llm-provider-strategy.md](docs/llm-provider-strategy.md) | `LLM_PROVIDER`, modos |
| [docs/llm-fallback-policy.md](docs/llm-fallback-policy.md) | Ordem de tentativas em falha |
| [docs/llm-response-contract.md](docs/llm-response-contract.md) | Formato `str \| None` |

---

## Módulos (`src/nbr12721/`)

| Módulo | Responsabilidade |
|--------|------------------|
| `main.py` | Entrypoint do pacote (`main()` usado por debug e `python -m nbr12721`) |
| `__main__.py` | Compatibilidade para `python -m nbr12721` |
| `logging_setup.py` | Console + arquivo `logs/*.log` (rotação) |
| `pipeline.py` | Orquestração do fluxo |
| `config.py` | Paths, limites, resolvers de provider/modelo |
| `prompts.py` | Prompts LLM |
| `llm.py` | Cliente multi-provider (`chamar_llm`) |
| `pdf_processing.py` | Extração PDF, OCR, pré-filtragem |
| `serialization.py` | Parse JSON e compactação de resumos |
| `cub.py` | Coleta e formatação de dados CUB |
| `excel_writer.py` | Preenchimento da planilha Excel |
| `formatacao.py` | Formatação BRL |

---

## Testes

```bash
pip install -e .   # opcional
./run_tests.sh
# ou: PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Mapa da suite: [tests/README.md](tests/README.md).
