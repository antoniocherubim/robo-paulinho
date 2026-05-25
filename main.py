"""Executa o pipeline a partir da raiz do projeto.

Este arquivo facilita debug em IDEs: configure este `main.py` como script
principal e use argumentos como `--skip-extracao` quando precisar.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nbr12721.main import main


if __name__ == "__main__":
    main()
