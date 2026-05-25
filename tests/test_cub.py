import unittest

from nbr12721.integrations.cub import extrair_valores_cub


TEXTO_CUB_RESIDENCIAL = """
R-1 2511,14  R-1 3143,09  R-1 3975,68
PP-4 2100,00  PP-4 2200,00  PP-4 2300,00
R-8 2400,00  R-8 2568,85  R-8 2700,00
R-16 2300,00  R-16 2492,09  R-16 2600,00
"""


class TestExtrairValoresCub(unittest.TestCase):
    def test_parse_linhas_residencial_tripla(self):
        valores = extrair_valores_cub(TEXTO_CUB_RESIDENCIAL)
        self.assertAlmostEqual(valores["R1-N"], 3143.09)
        self.assertAlmostEqual(valores["R8-N"], 2568.85)
        self.assertAlmostEqual(valores["R16-N"], 2492.09)
        self.assertAlmostEqual(valores["PP4-N"], 2200.00)


if __name__ == "__main__":
    unittest.main()
