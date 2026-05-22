"""Configuracao central de logging: console + arquivo em logs/."""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
_CONFIGURADO = False


def reset_logging() -> None:
    """Reinicia estado (util em testes)."""
    global _CONFIGURADO
    _CONFIGURADO = False
    logger_raiz = logging.getLogger("nbr12721")
    logger_raiz.handlers.clear()

_FORMATO = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_FORMATO_DATA = "%Y-%m-%d %H:%M:%S"
_LOG_MAX_BYTES = 5_000_000
_LOG_BACKUP_COUNT = 5


def _resolver_pasta_logs() -> Path:
    bruto = os.environ.get("PASTA_LOGS", "logs").strip() or "logs"
    pasta = Path(bruto)
    if not pasta.is_absolute():
        pasta = RAIZ_PROJETO / pasta
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def configurar_logging() -> Path:
    """Configura logger raiz nbr12721 (idempotente). Retorna caminho do arquivo .log."""
    global _CONFIGURADO
    pasta_logs = _resolver_pasta_logs()
    nome_arquivo = os.environ.get("LOG_ARQUIVO", "nbr12721.log").strip() or "nbr12721.log"
    caminho_log = pasta_logs / nome_arquivo

    nivel_nome = os.environ.get("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    nivel = getattr(logging, nivel_nome, logging.INFO)

    formatter = logging.Formatter(_FORMATO, datefmt=_FORMATO_DATA)

    logger_raiz = logging.getLogger("nbr12721")
    if _CONFIGURADO:
        return caminho_log

    logger_raiz.setLevel(nivel)
    logger_raiz.handlers.clear()
    logger_raiz.propagate = False

    arquivo = RotatingFileHandler(
        caminho_log,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    arquivo.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    logger_raiz.addHandler(arquivo)
    logger_raiz.addHandler(console)

    logging.getLogger("nbr12721").setLevel(nivel)
    _CONFIGURADO = True

    logger_raiz.info("Logging iniciado | arquivo=%s | nivel=%s", caminho_log, nivel_nome)
    return caminho_log
