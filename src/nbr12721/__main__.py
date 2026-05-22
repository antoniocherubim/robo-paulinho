"""Entrypoint: python -m nbr12721"""
import asyncio

from .logging_setup import configurar_logging
from .pipeline import executar_pipeline


def main():
    configurar_logging()
    asyncio.run(executar_pipeline())


if __name__ == "__main__":
    main()
