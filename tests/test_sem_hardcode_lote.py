"""Garante ausencia de strings do lote AY0410 em codigo de producao."""
import unittest
from pathlib import Path

TERMOS_PROIBIDOS = (
    "PAGOTTO",
    "YTICON",
    "LONDRINA",
    "PALHANO",
    "AY0410",
    "PR-27711",
)

# Integracao regional explicita; ignorar se a lista crescer com termos de fonte.
ARQUIVOS_IGNORADOS = {
    "integrations/cub.py",
}


class TestSemHardcodeLote(unittest.TestCase):
    def test_src_sem_strings_do_lote(self):
        raiz = Path(__file__).resolve().parents[1] / "src" / "nbr12721"
        violacoes: list[str] = []

        for caminho in sorted(raiz.rglob("*.py")):
            rel = caminho.relative_to(raiz).as_posix()
            if rel in ARQUIVOS_IGNORADOS:
                continue
            texto = caminho.read_text(encoding="utf-8")
            for numero, linha in enumerate(texto.splitlines(), start=1):
                upper = linha.upper()
                for termo in TERMOS_PROIBIDOS:
                    if termo in upper:
                        violacoes.append(f"{rel}:{numero}: {termo}")

        if violacoes:
            self.fail(
                "Strings do lote encontradas em src/nbr12721:\n"
                + "\n".join(violacoes[:30])
            )


if __name__ == "__main__":
    unittest.main()
