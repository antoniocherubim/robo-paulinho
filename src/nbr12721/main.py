"""Entrypoint principal do pipeline NBR 12721."""
import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nbr12721.logging_setup import configurar_logging
from nbr12721.pipeline import executar_pipeline

__all__ = ["main"]


def main():
    configurar_logging()
    asyncio.run(executar_pipeline())


if __name__ == "__main__":
    main()
