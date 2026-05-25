"""NBR 12721:2006 — preenchimento automatico de planilha com LLM."""
from .orchestration.pipeline import executar_pipeline

__all__ = ["executar_pipeline"]
