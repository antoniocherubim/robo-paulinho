import unittest

from nbr12721.formatacao import formatar_brl


class TestFormatarBrl(unittest.TestCase):
    def test_valor_simples(self):
        self.assertEqual(formatar_brl(1234.5), "1.234,50")

    def test_zero(self):
        self.assertEqual(formatar_brl(0), "0,00")


if __name__ == "__main__":
    unittest.main()
