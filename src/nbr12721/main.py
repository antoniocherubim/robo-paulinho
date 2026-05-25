"""Entrypoint principal do pipeline NBR 12721."""
import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nbr12721.orchestration.pipeline import executar_pipeline
from nbr12721.settings.logging_setup import configurar_logging

__all__ = ["main"]


def main():
    configurar_logging()
    asyncio.run(executar_pipeline())


if __name__ == "__main__":
    main()
