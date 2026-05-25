import json
import unittest

from nbr12721.extraction.serialization import compactar_resumos, parsear_json


class TestParsearJson(unittest.TestCase):
    def test_lixo_ao_redor(self):
        self.assertEqual(parsear_json('abc {"x": 1} xyz'), {"x": 1})

    def test_markdown_fence(self):
        self.assertEqual(parsear_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_sem_json(self):
        with self.assertRaises(json.JSONDecodeError):
            parsear_json("sem json aqui")


class TestCompactarResumos(unittest.TestCase):
    def test_estrutura_lote(self):
        texto = compactar_resumos([
            {
                "resumo": {"projeto": ["Edificio X"]},
                "dados_numericos": [],
                "pendencias": [],
            }
        ])
        self.assertIn("LOTE 1:", texto)
        self.assertIn("[projeto]", texto)
        self.assertIn("- Edificio X", texto)


if __name__ == "__main__":
    unittest.main()
