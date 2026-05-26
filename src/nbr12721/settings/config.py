"""Configuracao operacional do pipeline NBR 12721."""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

RAIZ_PROJETO = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - fallback para ambientes sem python-dotenv
    load_dotenv = None

if load_dotenv:
    load_dotenv(RAIZ_PROJETO / ".env")


def _resolver_path_env(nome: str, padrao_relativo: str) -> str:
    bruto = os.environ.get(nome, "").strip()
    if bruto:
        caminho = Path(bruto)
        if not caminho.is_absolute():
            caminho = RAIZ_PROJETO / caminho
        return str(caminho)
    return str(RAIZ_PROJETO / padrao_relativo)


def _resolver_path_env_opcional(nome: str) -> str | None:
    bruto = os.environ.get(nome, "").strip()
    if not bruto:
        return None
    caminho = Path(bruto)
    if not caminho.is_absolute():
        caminho = RAIZ_PROJETO / caminho
    return str(caminho)


def _resolver_int_env(nome: str, padrao: int) -> int:
    bruto = os.environ.get(nome, "").strip()
    if not bruto:
        return padrao
    try:
        valor = int(bruto)
    except ValueError:
        logger.warning("%s invalido (%r), usando %s", nome, bruto, padrao)
        return padrao
    return valor if valor > 0 else padrao


def _resolver_bool_env(nome: str, padrao: bool) -> bool:
    bruto = os.environ.get(nome, "").strip().lower()
    if not bruto:
        return padrao
    if bruto in {"1", "true", "t", "yes", "y", "sim", "s"}:
        return True
    if bruto in {"0", "false", "f", "no", "n", "nao", "não"}:
        return False
    logger.warning("%s invalido (%r), usando %s", nome, bruto, padrao)
    return padrao


# --- Diretorios e planilha modelo ---
PASTA_DOCS = _resolver_path_env("PASTA_DOCS", "data/input/documentos")
PASTA_SAIDA = _resolver_path_env("PASTA_SAIDA", "data/output/saida")
PLANILHA = _resolver_path_env("PLANILHA", "assets/ABNT_NBR_12721-2006.xlsx")
PASTA_LOGS = _resolver_path_env("PASTA_LOGS", "logs")

# --- OCR / PDF rasterizado ---
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "").strip() or None
TESSERACT_LANG = os.environ.get("TESSERACT_LANG", "").strip() or "por+eng"
POPPLER_PATH = _resolver_path_env_opcional("POPPLER_PATH")
OCR_DPI = _resolver_int_env("OCR_DPI", 150)
OCR_MIN_CHARS_PAGINA = _resolver_int_env("OCR_MIN_CHARS_PAGINA", 80)
OCR_USAR_ARQUIVOS_TEMP = _resolver_bool_env("OCR_USAR_ARQUIVOS_TEMP", True)
OCR_GRAYSCALE = _resolver_bool_env("OCR_GRAYSCALE", True)
OCR_TIMEOUT_SEGUNDOS = _resolver_int_env("OCR_TIMEOUT_SEGUNDOS", 120)
OCR_MAX_IMAGE_PIXELS = _resolver_int_env("OCR_MAX_IMAGE_PIXELS", 120_000_000)

# --- Extracao deterministica (sem LLM) ---
EXTRACAO_DETERMINISTICA = _resolver_bool_env("EXTRACAO_DETERMINISTICA", False)

# --- Artefatos de saida (basename) ---
ARQ_PLANILHA_SAIDA = "NBR_12721_preenchida.xlsx"
ARQ_TEXTO_EXTRAIDO = "textos_extraidos.txt"
ARQ_TEXTO_FILTRADO = "textos_filtrados.txt"
ARQ_RESUMOS_LOTES = "resumos_lotes.txt"
ARQ_RESPOSTA_BRUTA = "resposta_bruta.txt"
ARQ_DADOS_JSON = "dados_extraidos.json"
ARQ_VALIDACAO_JSON = "validacao_dados.json"
ARQ_AUDITORIA_PLANILHA_JSON = "auditoria_planilha.json"

# --- Validacao de completude do JSON ---
VALIDACAO_BLOQUEANTE = _resolver_bool_env("VALIDACAO_BLOQUEANTE", False)

# --- Auditoria pos-preenchimento da planilha ---
AUDITORIA_PLANILHA = _resolver_bool_env("AUDITORIA_PLANILHA", True)

# --- Fallback LLM apos extracao deterministica invalida ---
FALLBACK_LLM_SE_INVALIDO = _resolver_bool_env("FALLBACK_LLM_SE_INVALIDO", False)

# --- Limites de texto (pipeline LLM) ---
LIMITE_CHARS_LOTE = 18000
LIMITE_CHARS_PROMPT_FINAL = 60000
LIMITE_CHARS_CUB_TEXTO_COMPLETO = 4000
LIMITE_CHARS_TEXTO_FILTRADO = _resolver_int_env("LIMITE_CHARS_TEXTO_FILTRADO", 16000)

# --- Timeouts (segundos) ---
TIMEOUT_HTTP_SCRAPE = 15
TIMEOUT_HTTP_DOWNLOAD = 30
TIMEOUT_CLAUDE_SDK = 600
TIMEOUT_CLAUDE_CLI = 300

# --- Anthropic API ---
MODELO_ANTHROPIC_PADRAO = "claude-3-5-sonnet-20241022"
MAX_TOKENS_API = 4096
API_MAX_TENTATIVAS = 4
API_BACKOFF_BASE_SEG = 3
API_BACKOFF_MAX_SEG = 20

# --- Selecao de provider LLM ---
LLM_PROVIDER_VALIDOS = frozenset({"anthropic", "openai", "auto"})
LLM_AUTO_PRIMARY_VALIDOS = frozenset({"anthropic", "openai"})
LLM_PROVIDER_PADRAO = "anthropic"
LLM_AUTO_PRIMARY_PADRAO = "anthropic"

# --- OpenAI API ---
MODELO_OPENAI_PADRAO = "gpt-4o"


def resolver_openai_model() -> str:
    return os.environ.get("OPENAI_MODEL", "").strip() or MODELO_OPENAI_PADRAO


def resolver_llm_provider() -> str:
    """Retorna anthropic, openai ou auto. Valor invalido -> aviso + anthropic."""
    bruto = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if not bruto:
        return LLM_PROVIDER_PADRAO
    if bruto in LLM_PROVIDER_VALIDOS:
        return bruto
    logger.warning("LLM_PROVIDER invalido (%r), usando %s", bruto, LLM_PROVIDER_PADRAO)
    return LLM_PROVIDER_PADRAO


def resolver_llm_auto_primary() -> str:
    """Retorna anthropic ou openai. Valor invalido -> aviso + anthropic."""
    bruto = os.environ.get("LLM_AUTO_PRIMARY", "").strip().lower()
    if not bruto:
        return LLM_AUTO_PRIMARY_PADRAO
    if bruto in LLM_AUTO_PRIMARY_VALIDOS:
        return bruto
    logger.warning("LLM_AUTO_PRIMARY invalido (%r), usando %s", bruto, LLM_AUTO_PRIMARY_PADRAO)
    return LLM_AUTO_PRIMARY_PADRAO


def caminho_saida(nome_arquivo: str) -> str:
    return os.path.join(PASTA_SAIDA, nome_arquivo)
