"""NBR 12721:2006 — preenchimento automatico de planilha."""
import asyncio

from .orchestration.pipeline import executar_pipeline
from .settings.logging_setup import configurar_logging

__all__ = ["executar_pipeline", "main"]


def main() -> None:
    configurar_logging()
    asyncio.run(executar_pipeline())
