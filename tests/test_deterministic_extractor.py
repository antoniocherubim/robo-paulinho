import unittest

from nbr12721.deterministic_extractor import (
    _esqueleto_vazio,
    _normalizar_cnpj,
    _normalizar_crea,
    extrair_dados_deterministico,
)

TEXTO_SINTETICO = """
CNPJ10.910.7480001-85
LONDRINA-PR
24/07/2023
Nº de ALVARÁ: 2457/2023
TERRENO: 8.958,97 M2
EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]
CREAPR-27711D
"""


class TestDeterministicExtractor(unittest.TestCase):
    def test_extrai_campos_minimos_texto_sintetico(self):
        dados = extrair_dados_deterministico(TEXTO_SINTETICO)

        self.assertEqual(dados["incorporador"]["cnpj"], "10.910.748/0001-85")
        self.assertEqual(dados["projeto"]["cidadeUf"], "Londrina-PR")
        self.assertEqual(dados["projeto"]["dataAprovacao"], "24/07/2023")
        self.assertEqual(dados["projeto"]["numAlvara"], "2457/2023")
        self.assertAlmostEqual(dados["projeto"]["areaTerreno"], 8958.97)
        self.assertTrue(dados["projeto"]["projetoPadrao"]["R"])
        self.assertEqual(
            dados["quadro3"]["projetoPadrao"]["designacao"],
            "EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]",
        )
        self.assertEqual(dados["responsavel"]["crea"], "PR-27711/D")
        self.assertEqual(dados["_dados_faltantes"], [])

    def test_normaliza_cnpj_sem_barra(self):
        self.assertEqual(
            _normalizar_cnpj("CNPJ10.910.7480001-85"),
            "10.910.748/0001-85",
        )

    def test_normaliza_crea_ocr(self):
        self.assertEqual(_normalizar_crea("CREAPR-27711D"), "PR-27711/D")

    def test_normaliza_crea_com_espacos(self):
        self.assertEqual(_normalizar_crea("CREA PR-27711/D"), "PR-27711/D")

    def test_import_sem_efeitos_colaterais(self):
        import nbr12721.deterministic_extractor as mod

        self.assertEqual(mod.__all__, ["extrair_dados_deterministico"])
        vazio = extrair_dados_deterministico("")
        self.assertIn("incorporador", vazio)
        self.assertIn("projeto", vazio)
        self.assertIn("quadro3", vazio)
        self.assertIn("_dados_faltantes", vazio)

    def test_esqueleto_vazio_nao_compartilha_referencias(self):
        a = _esqueleto_vazio()
        b = _esqueleto_vazio()
        a["quadro1"]["pavimentos"][0]["nome"] = "X"
        a["quadro4a"]["unidadesSubrogadas"].append({"x": 1})
        self.assertEqual(b["quadro1"]["pavimentos"][0]["nome"], "")
        self.assertEqual(b["quadro4a"]["unidadesSubrogadas"], [])

    def test_dados_faltantes_paths_schema(self):
        dados = extrair_dados_deterministico("texto sem campos relevantes")
        esperados = {
            "incorporador.cnpj",
            "projeto.cidadeUf",
            "projeto.dataAprovacao",
            "projeto.numAlvara",
            "projeto.areaTerreno",
            "projeto.projetoPadrao.R",
            "quadro3.projetoPadrao.designacao",
        }
        self.assertTrue(esperados.issubset(set(dados["_dados_faltantes"])))
        self.assertNotIn("responsavel.crea", dados["_dados_faltantes"])

    def test_dados_faltantes_crea_quando_mencionado_e_nao_extraido(self):
        dados = extrair_dados_deterministico("CREA texto invalido xyz")
        self.assertIn("responsavel.crea", dados["_dados_faltantes"])

    def test_prioriza_data_em_linha_com_aprovacao(self):
        texto = """
10/01/2020
APROVAÇÃO DO PROJETO EM 24/07/2023
LONDRINA-PR
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["dataAprovacao"], "24/07/2023")

    def test_cidade_uf_nao_cruza_linha_crea(self):
        texto = "CREA PR-27711/D\nLONDRINA-PR"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["cidadeUf"], "Londrina-PR")

    def test_prioriza_data_proxima_alvara_em_linhas_vizinhas(self):
        texto = """
10/01/2020
Nº de ALVARÁ: 2457/2023
24/07/2023
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["dataAprovacao"], "24/07/2023")


if __name__ == "__main__":
    unittest.main()
