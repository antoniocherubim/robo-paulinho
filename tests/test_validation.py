import unittest

from nbr12721.extraction.validation import validar_dados_extraidos


def _unidades_tipo_quadro2() -> list[dict]:
    return [
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
        },
        {
            "designacao": "Apartamento tipo 65,985 m²",
            "areaPrivCobPadrao": 65.985,
            "areaPrivCobDifReal": 0,
            "areaPrivCobDifEquiv": 0,
            "areaComumNPCobPadrao": 0,
            "areaComumNPCobDifReal": 0,
            "areaComumNPCobDifEquiv": 0,
            "qtdUnidades": 80,
            "outrasAreasPriv": 0,
            "areaTerrExcl": 0,
            "areaTerrComum": 0,
        },
        {
            "designacao": "Apartamento tipo 55,00 m²",
            "areaPrivCobPadrao": 55.0,
            "areaPrivCobDifReal": 0,
            "areaPrivCobDifEquiv": 0,
            "areaComumNPCobPadrao": 0,
            "areaComumNPCobDifReal": 0,
            "areaComumNPCobDifEquiv": 0,
            "qtdUnidades": 80,
            "outrasAreasPriv": 0,
            "areaTerrExcl": 0,
            "areaTerrComum": 0,
        },
    ]


def _dados_minimos_completos() -> dict:
    return {
        "incorporador": {
            "nome": "ACME INCORPORAÇÃO LTDA",
            "cnpj": "12.345.678/0001-90",
            "endereco": "",
        },
        "responsavel": {
            "nome": "MARIA DE SOUZA PEREIRA",
            "crea": "",
            "art": "",
            "endereco": "",
        },
        "projeto": {
            "nomeEdificio": "RESIDENCIAL ALPHA",
            "localConstrucao": "LOTE 22, BAIRRO CENTRO",
            "cidadeUf": "Curitiba-PR",
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
                    "areaPrivCobPadrao": 1012.1,
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
            "unidades": _unidades_tipo_quadro2(),
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


def _dados_quadro1_tipo_base(**overrides_pavimento) -> dict:
    dados = _dados_minimos_completos()
    pavimento = dados["quadro1"]["pavimentos"][0]
    pavimento.update(overrides_pavimento)
    return dados


class TestValidarDadosExtraidos(unittest.TestCase):
    def test_valida_dados_completos_ok(self):
        resultado = validar_dados_extraidos(_dados_minimos_completos())
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["criticos_faltantes"], [])
        self.assertEqual(resultado["inconsistencias"], [])
        self.assertLessEqual(resultado["score"], 1)
        self.assertGreater(resultado["score"], 0.7)

    def test_detecta_criticos_faltantes(self):
        resultado = validar_dados_extraidos({})
        self.assertFalse(resultado["ok"])
        self.assertIn("incorporador.cnpj", resultado["criticos_faltantes"])
        self.assertIn("projeto.qtdUnidades", resultado["criticos_faltantes"])
        self.assertIn("quadro1.pavimentos", resultado["criticos_faltantes"])
        self.assertIn("quadro2.unidades", resultado["criticos_faltantes"])
        self.assertEqual(resultado["inconsistencias"], [])

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

    def test_inconsistencia_quadro1_area_tipo_duplicada(self):
        dados = _dados_quadro1_tipo_base(
            areaPrivCobPadrao=20242.0,
            qtdPavimentos=20,
        )
        resultado = validar_dados_extraidos(dados)
        self.assertIn(
            "quadro1.pavimentos.area_tipo_possivelmente_total_duplicada",
            resultado["inconsistencias"],
        )
        self.assertTrue(resultado["ok"])

    def test_quadro1_area_tipo_por_pavimento_sem_inconsistencia(self):
        dados = _dados_quadro1_tipo_base(
            areaPrivCobPadrao=1012.1,
            qtdPavimentos=20,
        )
        resultado = validar_dados_extraidos(dados)
        self.assertNotIn(
            "quadro1.pavimentos.area_tipo_possivelmente_total_duplicada",
            resultado["inconsistencias"],
        )


if __name__ == "__main__":
    unittest.main()
