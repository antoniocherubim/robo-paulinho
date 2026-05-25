"""Flags de execucao do pipeline NBR 12721."""
import sys

from ..settings.config import EXTRACAO_DETERMINISTICA, FALLBACK_LLM_SE_INVALIDO

__all__ = [
    "somente_json",
    "usar_extracao_deterministica",
    "usar_fallback_llm",
]


def usar_extracao_deterministica(argv=None) -> bool:
    argv = sys.argv if argv is None else argv
    return EXTRACAO_DETERMINISTICA or "--deterministico" in argv


def somente_json(argv=None) -> bool:
    argv = sys.argv if argv is None else argv
    return "--json-only" in argv


def usar_fallback_llm(argv=None) -> bool:
    argv = sys.argv if argv is None else argv
    return FALLBACK_LLM_SE_INVALIDO or "--fallback-llm" in argv
