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
        self.assertIn("projeto.qtdUnidades", dados["_dados_faltantes"])
        self.assertIn("projeto.numPavimentos", dados["_dados_faltantes"])

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

    def test_extrai_qtd_unidades_por_areas(self):
        texto = """
(1º AO 20º) PAV. TIPO - 66,02 X 160 APTOS
(1º AO 20º) PAV. TIPO - 65,985 X 80 APTOS
(1º AO 20º) PAV. TIPO - 55,00 X 80 APTOS
"""
        dados = extrair_dados_deterministico(texto)
        unidades = dados["quadro2"]["unidades"]

        self.assertEqual(dados["projeto"]["qtdUnidades"], 320)
        self.assertEqual(len(unidades), 3)
        self.assertAlmostEqual(unidades[0]["areaPrivCobPadrao"], 55.0)
        self.assertAlmostEqual(unidades[1]["areaPrivCobPadrao"], 65.985)
        self.assertAlmostEqual(unidades[2]["areaPrivCobPadrao"], 66.02)
        self.assertEqual(unidades[0]["qtdUnidades"], 80)
        self.assertEqual(unidades[1]["qtdUnidades"], 80)
        self.assertEqual(unidades[2]["qtdUnidades"], 160)

    def test_nao_duplica_unidade_repetida_por_ocr(self):
        linha = "(1º AO 20º) PAV. TIPO - 66,02 X 160 APTOS"
        texto = f"{linha}\n{linha}"
        dados = extrair_dados_deterministico(texto)

        self.assertEqual(dados["projeto"]["qtdUnidades"], 160)
        self.assertEqual(len(dados["quadro2"]["unidades"]), 1)

    def test_extrai_qtd_unidades_sem_area(self):
        dados = extrair_dados_deterministico("160 APTOS")
        self.assertEqual(dados["projeto"]["qtdUnidades"], 160)
        self.assertEqual(dados["quadro2"]["unidades"][0]["designacao"], "")

    def test_aptos_por_pav_nao_conta_como_qtd_total(self):
        dados = extrair_dados_deterministico("6 APTOS/PAV")
        self.assertEqual(dados["projeto"]["qtdUnidades"], 0)
        self.assertEqual(dados["quadro5"]["unidadesPorPav"], "6 APTOS/PAV")

    def test_qtd_sem_area_nao_duplica_qtd_com_area(self):
        texto = "66,02 X 160 APTOS\n160 APTOS"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["qtdUnidades"], 160)

    def test_extrai_num_pavimentos_com_terreo_e_cobertura(self):
        texto = """
PAVIMENTO TÉRREO
(1º AO 20º) PAV. TIPO
COBERTURA
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["numPavimentos"], 22)
        self.assertEqual(dados["quadro5"]["numPavimentos"], "22")

    def test_extrai_vagas_comuns_e_duplas_maior_valor(self):
        texto = """
TOTAL DE VAGAS COMUNS: 50 VAGAS
TOTAL DE VAGAS COMUNS: 55 VAGAS
TOTAL DE VAGAS DUPLAS: 21 VAGAS
TOTAL DE VAGAS DUPLAS: 13 VAGAS
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["vagasComum"], 55)
        self.assertEqual(dados["projeto"]["vagasAcessorio"], 21)
        self.assertEqual(
            dados["quadro5"]["garagens"],
            "55 vagas comuns; 21 vagas duplas",
        )

    def test_quadro5_copia_dados_basicos(self):
        texto = """
EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]
24/07/2023
PAVIMENTO TÉRREO
(1º AO 20º) PAV. TIPO
COBERTURA
TOTAL DE VAGAS COMUNS: 55 VAGAS
TOTAL DE VAGAS DUPLAS: 21 VAGAS
6 APTOS/PAV
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["quadro5"]["tipoEdificacao"],
            "EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]",
        )
        self.assertEqual(dados["quadro5"]["dataAprovacao"], "24/07/2023")
        self.assertEqual(dados["quadro5"]["numPavimentos"], "22")
        self.assertEqual(
            dados["quadro5"]["garagens"],
            "55 vagas comuns; 21 vagas duplas",
        )
        self.assertEqual(dados["quadro5"]["unidadesPorPav"], "6 APTOS/PAV")


if __name__ == "__main__":
    unittest.main()
