import unittest
from unittest.mock import patch

from nbr12721.pipeline import (
    _preencher_cub_automatico,
    _somente_json,
    _usar_extracao_deterministica,
)


class TestPipelineModes(unittest.TestCase):
    def test_usar_extracao_deterministica_por_flag(self):
        with patch("nbr12721.pipeline.EXTRACAO_DETERMINISTICA", False):
            self.assertTrue(
                _usar_extracao_deterministica(["prog", "--deterministico"])
            )
            self.assertFalse(_usar_extracao_deterministica(["prog"]))

    def test_somente_json_por_flag(self):
        self.assertTrue(_somente_json(["prog", "--json-only"]))
        self.assertFalse(_somente_json(["prog"]))

    def test_preencher_cub_automatico_residencial(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "sindicato": "",
                "mesCub": "",
                "valorCub": 0,
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {"R4-N": 2500.55, "R1-N": 2300.10},
        }
        _preencher_cub_automatico(dados, cub_info)
        self.assertEqual(dados["quadro3"]["valorCub"], 2500.55)
        self.assertEqual(dados["quadro3"]["sindicato"], "SINDUSCON NORTE PR")
        self.assertEqual(dados["quadro3"]["mesCub"], "Abril/2026")

    def test_preencher_cub_nao_sobrescreve_valor_existente(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "valorCub": 999,
                "sindicato": "",
                "mesCub": "",
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {"R4-N": 2500.55},
        }
        _preencher_cub_automatico(dados, cub_info)
        self.assertEqual(dados["quadro3"]["valorCub"], 999)


if __name__ == "__main__":
    unittest.main()
