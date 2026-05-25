import unittest

from nbr12721.extraction.validation import validar_dados_extraidos


def _dados_minimos_completos() -> dict:
    return {
        "incorporador": {
            "nome": "MARCELO PAGOTTO",
            "cnpj": "10.910.748/0001-85",
            "endereco": "",
        },
        "responsavel": {
            "nome": "IVAN I. GONÇALVES DA SILVA",
            "crea": "",
            "art": "",
            "endereco": "",
        },
        "projeto": {
            "nomeEdificio": "RESIDENCIAL ALPHA",
            "localConstrucao": "RIBEIRÃO DA ESPERANÇA, FAZENDA PALHANO",
            "cidadeUf": "Londrina-PR",
            "projetoPadrao": {
                "R": True,
                "CS": False,
                "CL": False,
                "CG": False,
                "CP": False,
                "CP1Q": False,
            },
            "qtdUnidades": 320,
            "numPavimentos": 22,
            "vagasUA": 0,
            "vagasAcessorio": 21,
            "vagasComum": 55,
            "areaTerreno": 8958.97,
            "dataAprovacao": "",
            "numAlvara": "2457/2023",
        },
        "quadro1": {
            "pavimentos": [
                {
                    "nome": "Pavimentos tipo",
                    "areaPrivCobPadrao": 20242.0,
                    "areaPrivCobDifReal": 0,
                    "areaPrivCobDifEquiv": 0,
                    "areaComumNPCobPadrao": 0,
                    "areaComumNPCobDifReal": 0,
                    "areaComumNPCobDifEquiv": 0,
                    "areaComumPCobPadrao": 0,
                    "areaComumPCobDifReal": 0,
                    "areaComumPCobDifEquiv": 0,
                    "qtdPavimentos": 20,
                }
            ],
        },
        "quadro2": {
            "unidades": [
                {
                    "designacao": "Apartamento tipo 66,02 m²",
                    "areaPrivCobPadrao": 66.02,
                    "areaPrivCobDifReal": 0,
                    "areaPrivCobDifEquiv": 0,
                    "areaComumNPCobPadrao": 0,
                    "areaComumNPCobDifReal": 0,
                    "areaComumNPCobDifEquiv": 0,
                    "qtdUnidades": 160,
                    "outrasAreasPriv": 0,
                    "areaTerrExcl": 0,
                    "areaTerrComum": 0,
                }
            ],
        },
        "quadro3": {
            "projetoPadrao": {"padrao": ""},
            "valorCub": 2500.55,
            "sindicato": "",
            "mesCub": "",
        },
        "quadro5": {
            "tipoEdificacao": "EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]",
            "garagens": "55 vagas comuns; 21 vagas duplas",
        },
    }


class TestValidarDadosExtraidos(unittest.TestCase):
    def test_valida_dados_completos_ok(self):
        resultado = validar_dados_extraidos(_dados_minimos_completos())
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["criticos_faltantes"], [])
        self.assertLessEqual(resultado["score"], 1)
        self.assertGreater(resultado["score"], 0.7)

    def test_detecta_criticos_faltantes(self):
        resultado = validar_dados_extraidos({})
        self.assertFalse(resultado["ok"])
        self.assertIn("incorporador.cnpj", resultado["criticos_faltantes"])
        self.assertIn("projeto.qtdUnidades", resultado["criticos_faltantes"])
        self.assertIn("quadro1.pavimentos", resultado["criticos_faltantes"])
        self.assertIn("quadro2.unidades", resultado["criticos_faltantes"])

    def test_quadro1_template_conta_como_faltante(self):
        dados = {
            "quadro1": {
                "pavimentos": [
                    {
                        "nome": "",
                        "areaPrivCobPadrao": 0,
                        "qtdPavimentos": 1,
                    }
                ],
            },
        }
        resultado = validar_dados_extraidos(dados)
        self.assertIn("quadro1.pavimentos", resultado["criticos_faltantes"])

    def test_quadro1_item_nao_dict_conta_como_faltante(self):
        resultado = validar_dados_extraidos({"quadro1": {"pavimentos": [None]}})
        self.assertIn("quadro1.pavimentos", resultado["criticos_faltantes"])

    def test_quadro2_item_nao_dict_conta_como_faltante(self):
        resultado = validar_dados_extraidos({"quadro2": {"unidades": [None]}})
        self.assertIn("quadro2.unidades", resultado["criticos_faltantes"])

    def test_quadro2_template_conta_como_faltante(self):
        dados = {
            "quadro2": {
                "unidades": [
                    {
                        "designacao": "",
                        "areaPrivCobPadrao": 0,
                    }
                ],
            },
        }
        resultado = validar_dados_extraidos(dados)
        self.assertIn("quadro2.unidades", resultado["criticos_faltantes"])

    def test_avisos_nao_bloqueiam_ok(self):
        dados = _dados_minimos_completos()
        resultado = validar_dados_extraidos(dados)
        self.assertTrue(resultado["ok"])
        self.assertIn("responsavel.crea", resultado["avisos"])


if __name__ == "__main__":
    unittest.main()
