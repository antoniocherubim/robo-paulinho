"""Entrypoint unico do projeto NBR 12721."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbr12721.orchestration.pipeline import executar_pipeline
from nbr12721.settings.logging_setup import configurar_logging


def main() -> None:
    configurar_logging()
    asyncio.run(executar_pipeline())


if __name__ == "__main__":
    main()
