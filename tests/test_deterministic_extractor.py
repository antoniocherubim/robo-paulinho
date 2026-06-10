import unittest

from nbr12721.extraction.deterministic_extraction.extractor import (
    _esqueleto_vazio,
    _normalizar_cnpj,
    _normalizar_crea,
    extrair_dados_deterministico,
)

TEXTO_SINTETICO = """
CNPJ12.345.6780001-90
CURITIBA-PR
24/07/2023
Nº de ALVARÁ: 2457/2023
TERRENO: 8.958,97 M2
EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]
CREASP-54321D
"""


class TestDeterministicExtractor(unittest.TestCase):
    def test_extrai_campos_minimos_texto_sintetico(self):
        dados = extrair_dados_deterministico(TEXTO_SINTETICO)

        self.assertEqual(dados["incorporador"]["cnpj"], "12.345.678/0001-90")
        self.assertEqual(dados["projeto"]["cidadeUf"], "Curitiba-PR")
        self.assertEqual(dados["projeto"]["dataAprovacao"], "24/07/2023")
        self.assertEqual(dados["projeto"]["numAlvara"], "2457/2023")
        self.assertAlmostEqual(dados["projeto"]["areaTerreno"], 8958.97)
        self.assertTrue(dados["projeto"]["projetoPadrao"]["R"])
        self.assertEqual(
            dados["quadro3"]["projetoPadrao"]["designacao"],
            "EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]",
        )
        self.assertEqual(dados["responsavel"]["crea"], "SP-54321/D")
        self.assertIn("projeto.qtdUnidades", dados["_dados_faltantes"])
        self.assertIn("projeto.numPavimentos", dados["_dados_faltantes"])

    def test_normaliza_cnpj_sem_barra(self):
        self.assertEqual(
            _normalizar_cnpj("CNPJ10.910.7480001-85"),
            "10.910.748/0001-85",
        )

    def test_normaliza_crea_ocr(self):
        self.assertEqual(_normalizar_crea("CREASP-54321D"), "SP-54321/D")

    def test_normaliza_crea_com_espacos(self):
        self.assertEqual(_normalizar_crea("CREA SP-54321/D"), "SP-54321/D")

    def test_import_sem_efeitos_colaterais(self):
        import nbr12721.extraction.deterministic_extraction.extractor as mod

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
CURITIBA-PR
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["dataAprovacao"], "24/07/2023")

    def test_cidade_uf_nao_cruza_linha_crea(self):
        texto = "CREA SP-54321/D\nCURITIBA-PR"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["cidadeUf"], "Curitiba-PR")

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

    def test_normaliza_pavimento_ocr_20_graus_como_202(self):
        texto = """
PAVIMENTO TÉRREO
(1º AO 202) PAV. TIPO - 66,02 X 160 APTOS
COBERTURA
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["numPavimentos"], 22)
        self.assertEqual(dados["quadro1"]["pavimentos"][0]["qtdPavimentos"], 20)

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

    def test_extrai_vagas_com_separador_ponto(self):
        texto = """
TOTAL DE VAGAS COMUNS. 72 VAGAS
TOTAL DE VAGAS DUPLAS. 50 VAGAS
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["vagasComum"], 72)
        self.assertEqual(dados["projeto"]["vagasAcessorio"], 50)

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

    def test_extrai_local_construcao(self):
        texto = """
LOCAL DA OBRA: FAZENDA BOA VISTA, BAIRRO CENTRO
CURITIBA-PR
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["projeto"]["localConstrucao"],
            "FAZENDA BOA VISTA, BAIRRO CENTRO",
        )

    def test_extrai_responsavel_nome_crea(self):
        texto = (
            "MARIA DE SOUZA PEREIRA - ENGENHEIRA CIVIL - CREA SP-12345/D"
        )
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["responsavel"]["nome"],
            "MARIA DE SOUZA PEREIRA",
        )
        self.assertEqual(dados["responsavel"]["crea"], "SP-12345/D")

    def test_nao_inventa_nome_responsavel_sem_nome(self):
        texto = "ENGENHEIRA CIVIL - CREA SP-54321/D"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["responsavel"]["nome"], "")
        self.assertEqual(dados["responsavel"]["crea"], "SP-54321/D")

    def test_nao_usa_linha_administrativa_com_crea_como_responsavel(self):
        texto = (
            "Processo Aprovação nº 99.001/2024-01 "
            "JOÃO TESTE CREA SP-54321/D"
        )
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["responsavel"]["nome"], "")
        self.assertEqual(dados["responsavel"]["crea"], "SP-54321/D")

    def test_extrai_responsavel_endereco(self):
        texto = (
            "rua joão wyclif 111 sl 107 : 86050-450 palhano : "
            "londrina-pr : [43]3028-3990 : contato@vianiarquitetura.com.br"
        )
        dados = extrair_dados_deterministico(texto)
        self.assertIn(
            "rua joão wyclif 111",
            dados["responsavel"]["endereco"].lower(),
        )

    def test_extrai_incorporador_nome_por_rotulo(self):
        texto = """
PROPRIETÁRIO: ACME INCORPORAÇÃO LTDA
CNPJ 12.345.678/0001-90
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["nome"], "ACME INCORPORAÇÃO LTDA")

    def test_extrai_incorporador_perto_cnpj(self):
        texto = """
ALFA SPE LTDA
CNPJ 98.765.432/0001-11
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["nome"], "ALFA SPE LTDA")

    def test_incorporador_perto_cnpj_nao_usa_linha_so_com_data(self):
        texto = """
24/07/2023
BETA CONSTRUTORA LTDA
CNPJ 12.345.678/0001-90
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["nome"], "BETA CONSTRUTORA LTDA")

    def test_limpa_prefixo_numerico_nome_empresa(self):
        from nbr12721.extraction.deterministic_extraction.identity import (
            _limpar_nome_incorporador,
        )

        self.assertEqual(
            _limpar_nome_incorporador("7 ACME INCORPORAÇÃO LTDA"),
            "ACME INCORPORAÇÃO LTDA",
        )

    def test_limpa_prefixo_numerico_responsavel(self):
        texto = """
4 MARIA DE SOUZA PEREIRA
ENGENHEIRA CIVIL - CREA SP-12345/D
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["responsavel"]["nome"],
            "MARIA DE SOUZA PEREIRA",
        )

    def test_limpa_ruido_final_local_construcao(self):
        texto = """
LOCAL DA OBRA DATA DO PROJETO
LOTE 22, QUADRA 5, err
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["projeto"]["localConstrucao"],
            "LOTE 22, QUADRA 5",
        )

    def test_limpeza_textual_preserva_endereco_valido(self):
        texto = "RUA DAS FLORES, 123, BAIRRO CENTRO 80000-000"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["responsavel"]["endereco"],
            "RUA DAS FLORES, 123, BAIRRO CENTRO 80000-000",
        )

    def test_limpeza_textual_preserva_empresa_ltda(self):
        texto = "PROPRIETÁRIO: ACME INCORPORAÇÃO LTDA."
        dados = extrair_dados_deterministico(texto)
        self.assertIn("LTDA", dados["incorporador"]["nome"])

    def test_limpeza_textual_remove_prefixo_simbolico(self):
        texto = "LOCAL DA OBRA: | * FAZENDA BOA VISTA -"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["projeto"]["localConstrucao"],
            "FAZENDA BOA VISTA",
        )

    def test_incorporador_rejeita_linha_com_dados_admin(self):
        texto = """
Dados do empreendimento
ACME INCORPORAÇÃO LTDA
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["nome"], "")

    def test_processo_aprovacao_nao_preenche_incorporador(self):
        texto = "Processo Aprovação nº 99.001/2024 FULANO DA SILVA"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["nome"], "")

    def test_cidade_uf_multiplas_cidades(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_cidade_uf,
        )

        self.assertEqual(_extrair_cidade_uf("CURITIBA-PR"), "Curitiba-PR")
        self.assertEqual(_extrair_cidade_uf("SÃO PAULO-SP"), "São Paulo-SP")
        self.assertEqual(
            _extrair_cidade_uf("BELO HORIZONTE-MG"), "Belo Horizonte-MG"
        )

    def test_cidade_uf_com_prefixo_evidencia_na_mesma_linha(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_cidade_uf,
        )

        texto = "[projeto-xyz.pdf] CURITIBA-PR"
        self.assertEqual(_extrair_cidade_uf(texto), "Curitiba-PR")

    def test_alvara_prefere_formato_com_barra(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_num_alvara,
        )

        texto = "ALVARÁ: 245712029\nNº de ALVARÁ: 2457/2023"
        self.assertEqual(_extrair_num_alvara(texto), "2457/2023")

    def test_area_terreno_at_carimbo(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_area_terreno,
        )

        self.assertAlmostEqual(
            _extrair_area_terreno("ÁREA TERRENO [AT] 6.956,97"), 6956.97
        )
        self.assertAlmostEqual(
            _extrair_area_terreno("| t ÁREA TERRENO [AT]| 6.956,97"), 6956.97
        )

    def test_local_nao_aceita_cabecalho_taxa(self):
        texto = """
LOCAL DA OBRA DATA DO PROJETO TAXA DE OCUPAÇÃO
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["localConstrucao"], "")

    def test_local_consolida_lote_e_situado(self):
        texto = """
LOCAL DA OBRA DATA DO PROJETO TAXA DE OCUPAÇÃO
LOTE 22, QUADRA 5
SITUADO NO BAIRRO CENTRO, 61,77%
CURITIBA-PR
"""
        dados = extrair_dados_deterministico(texto)
        local = dados["projeto"]["localConstrucao"]
        self.assertIn("LOTE 22", local)
        self.assertIn("BAIRRO CENTRO", local)
        self.assertNotIn("61,77%", local)
        self.assertNotIn("Curitiba", local)

    def test_local_fazenda_generica(self):
        texto = "FAZENDA BOA VISTA, ESTRADA RURAL KM 12"
        dados = extrair_dados_deterministico(texto)
        self.assertIn("FAZENDA BOA VISTA", dados["projeto"]["localConstrucao"])

    def test_responsavel_nome_ocr_lixo_busca_linha_legivel(self):
        texto = """
ZON * ZON vo
MARIA DE SOUZA PEREIRA
DA SILVA TESTE TESTE
ENGENHEIRA CIVIL - CREA SP-12345/D
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            dados["responsavel"]["nome"],
            "MARIA DE SOUZA PEREIRA",
        )

    def test_responsavel_nao_aceita_zon_lixo(self):
        texto = "ZON * ZON vo ENGENHEIRA CIVIL - CREA SP-54321/D"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["responsavel"]["nome"], "")

    def test_extrai_nome_edificio_por_rotulo(self):
        texto = "NOME DO EDIFÍCIO: RESIDENCIAL ALPHA"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["nomeEdificio"], "RESIDENCIAL ALPHA")

    def test_cnpj_prefere_rotulado_com_mascara_ausente(self):
        texto = """
YTICON CONSTRUÇÃO E INCORPORAÇÃO LTDA 06020259103960001
CNPJ10.910.7480001-85
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["cnpj"], "10.910.748/0001-85")

    def test_cnpj_nao_pega_numero_solto_quando_sem_rotulo(self):
        texto = "EMPRESA EXEMPLO LTDA 12345678901234"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["incorporador"]["cnpj"], "")

    def test_cidade_uf_remove_prefixo_ocr_curto(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_cidade_uf,
        )

        self.assertEqual(_extrair_cidade_uf("Acd Londrina-PR"), "Londrina-PR")
        self.assertEqual(
            _extrair_cidade_uf("(aga (aad (asa (acd LONDRINA-PR 24/07/2023"),
            "Londrina-PR",
        )

    def test_cidade_uf_preserva_cidade_composta(self):
        from nbr12721.extraction.deterministic_extraction.base_fields import (
            _extrair_cidade_uf,
        )

        self.assertEqual(_extrair_cidade_uf("BELO HORIZONTE-MG"), "Belo Horizonte-MG")
        self.assertEqual(_extrair_cidade_uf("Rio de Janeiro-RJ"), "Rio De Janeiro-RJ")

    def test_nome_edificio_rejeita_habitese_condicionado(self):
        texto = """
O CERTIFICADO DE VISTORIA FICARA CONDICIONADO A
EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["nomeEdificio"], "")

    def test_nome_edificio_rejeita_emprendimento_com_condicinado(self):
        texto = "EMPREENDIMENTO, FICARA CONDICINADO A"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["projeto"]["nomeEdificio"], "")

    def test_endereco_remove_prefixo_arquivo_pdf(self):
        from nbr12721.extraction.deterministic_extraction.identity import (
            _extrair_responsavel_endereco,
        )

        texto = "[foo.pdf] Rua das Flores, 123, Centro, CEP 80000-000"
        self.assertEqual(
            _extrair_responsavel_endereco(texto),
            "Rua das Flores, 123, Centro, CEP 80000-000",
        )

    def test_nao_remove_rmv_no_meio(self):
        texto = "EDIFICAÇÃO RESIDENCIAL MULTIFAMILIAR VERTICAL [RMV]"
        dados = extrair_dados_deterministico(texto)
        self.assertIn(
            "[RMV]",
            dados["quadro3"]["projetoPadrao"]["designacao"],
        )

    def test_quadro5_outras_indicacoes(self):
        texto = """
Processo Aprovação nº 99.001/2024-06
Nº de ALVARÁ: 2457/2023
LOCAL DA OBRA: FAZENDA BOA VISTA, BAIRRO CENTRO
"""
        dados = extrair_dados_deterministico(texto)
        outras = dados["quadro5"]["outrasIndicacoes"]
        self.assertIn("99.001/2024-06", outras)
        self.assertIn("2457/2023", outras)
        self.assertIn("FAZENDA BOA VISTA", outras)

    def test_quadro1_extrai_pavimento_tipo_por_unidades(self):
        texto = """
(1º AO 20º) PAV. TIPO - 66,02 X 160 APTOS
(1º AO 20º) PAV. TIPO - 65,985 X 80 APTOS
(1º AO 20º) PAV. TIPO - 55,00 X 80 APTOS
"""
        dados = extrair_dados_deterministico(texto)
        pavs = dados["quadro1"]["pavimentos"]
        self.assertEqual(len(pavs), 1)
        self.assertEqual(pavs[0]["nome"], "Pavimentos tipo")
        self.assertAlmostEqual(pavs[0]["areaPrivCobPadrao"], 1012.1)
        self.assertEqual(pavs[0]["qtdPavimentos"], 20)
        self.assertAlmostEqual(
            pavs[0]["areaPrivCobPadrao"] * pavs[0]["qtdPavimentos"],
            20242.0,
        )

    def test_quadro1_area_tipo_total_reconstituida_por_multiplicacao(self):
        texto = """
(1º AO 20º) PAV. TIPO - 66,02 X 160 APTOS
(1º AO 20º) PAV. TIPO - 65,985 X 80 APTOS
(1º AO 20º) PAV. TIPO - 55,00 X 80 APTOS
"""
        dados = extrair_dados_deterministico(texto)
        item = dados["quadro1"]["pavimentos"][0]
        total_reconstituido = item["areaPrivCobPadrao"] * item["qtdPavimentos"]
        self.assertAlmostEqual(total_reconstituido, 20242.0, places=2)

    def test_quadro1_pavimento_tipo_nao_cria_sem_intervalo(self):
        texto = "66,02 X 160 APTOS"
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(dados["quadro1"]["pavimentos"][0]["nome"], "")

    def test_quadro1_extrai_terreo_lazer_coberto_descoberto(self):
        texto = """
ÁREA DE LAZER COBERTA PAV. TÉRREO = 1.275,94m²
ÁREA DE LAZER DESCOBERTA PAV. TÉRREO = 1.989,19m²
"""
        dados = extrair_dados_deterministico(texto)
        pav = dados["quadro1"]["pavimentos"][0]
        self.assertEqual(pav["nome"], "Pavimento térreo")
        self.assertAlmostEqual(pav["areaComumPCobPadrao"], 1275.94)
        self.assertAlmostEqual(pav["areaComumNPCobPadrao"], 1989.19)

    def test_quadro1_area_total_terreo_fallback(self):
        texto = "ÁREA PAVIMENTO TÉRREO: 4.211,29 m²"
        dados = extrair_dados_deterministico(texto)
        pav = dados["quadro1"]["pavimentos"][0]
        self.assertEqual(pav["nome"], "Pavimento térreo")
        self.assertAlmostEqual(pav["areaComumPCobPadrao"], 4211.29)
        self.assertAlmostEqual(pav["areaComumNPCobPadrao"], 0)

    def test_quadro1_extrai_cobertura_com_area(self):
        texto = "COBERTURA - ÁREA: 250,00 m²"
        dados = extrair_dados_deterministico(texto)
        pav = dados["quadro1"]["pavimentos"][0]
        self.assertEqual(pav["nome"], "Cobertura")
        self.assertAlmostEqual(pav["areaPrivCobPadrao"], 250.0)

    def test_quadro1_nao_cria_cobertura_sem_area(self):
        dados = extrair_dados_deterministico("COBERTURA")
        pav = dados["quadro1"]["pavimentos"][0]
        self.assertEqual(pav["nome"], "")
        self.assertIn("quadro1.pavimentos", dados["_dados_faltantes"])

    def test_quadro1_ordem_terreo_tipo_cobertura(self):
        texto = """
ÁREA DE LAZER COBERTA PAV. TÉRREO = 1.275,94m²
ÁREA DE LAZER DESCOBERTA PAV. TÉRREO = 1.989,19m²
(1º AO 20º) PAV. TIPO - 66,02 X 160 APTOS
(1º AO 20º) PAV. TIPO - 65,985 X 80 APTOS
(1º AO 20º) PAV. TIPO - 55,00 X 80 APTOS
COBERTURA - ÁREA: 250,00 m²
"""
        dados = extrair_dados_deterministico(texto)
        self.assertEqual(
            [p["nome"] for p in dados["quadro1"]["pavimentos"]],
            ["Pavimento térreo", "Pavimentos tipo", "Cobertura"],
        )


class TestLimparRuidoOcrTextual(unittest.TestCase):
    """Testes unitarios diretos do helper de saneamento pos-OCR."""

    def test_remove_token_err_apos_virgula(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(
            _limpar_ruido_ocr_textual("LOTE 22, QUADRA 5, err"),
            "LOTE 22, QUADRA 5",
        )

    def test_remove_prefixo_e_sufixo_simbolicos(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(
            _limpar_ruido_ocr_textual("| * FAZENDA BOA VISTA -"),
            "FAZENDA BOA VISTA",
        )

    def test_preserva_endereco_com_numeros(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        endereco = "RUA DAS FLORES, 123, BAIRRO CENTRO"
        self.assertEqual(_limpar_ruido_ocr_textual(endereco), endereco)

    def test_preserva_curitiba_pr(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(_limpar_ruido_ocr_textual("CURITIBA-PR"), "CURITIBA-PR")

    def test_preserva_ltda_sa_spe_uf(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(
            _limpar_ruido_ocr_textual("ACME INCORPORAÇÃO LTDA."),
            "ACME INCORPORAÇÃO LTDA.",
        )
        self.assertEqual(_limpar_ruido_ocr_textual("EMPRESA S/A"), "EMPRESA S/A")
        self.assertEqual(
            _limpar_ruido_ocr_textual("ALFA SPE LTDA"), "ALFA SPE LTDA"
        )
        self.assertEqual(_limpar_ruido_ocr_textual("FILIAL, PR"), "FILIAL, PR")

    def test_loop_remove_varios_segmentos_ruido(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(_limpar_ruido_ocr_textual("LOTE 1, err, e"), "LOTE 1")

    def test_normaliza_virgulas_repetidas_e_final(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(
            _limpar_ruido_ocr_textual("FAZENDA BOA VISTA,, BAIRRO CENTRO,"),
            "FAZENDA BOA VISTA, BAIRRO CENTRO",
        )

    def test_remove_err_em_linha_com_rotulo_local(self):
        from nbr12721.extraction.deterministic_extraction.utils import (
            _limpar_ruido_ocr_textual,
        )

        self.assertEqual(
            _limpar_ruido_ocr_textual("LOCAL DA OBRA: LOTE 22, QUADRA 5, err"),
            "LOCAL DA OBRA: LOTE 22, QUADRA 5",
        )


if __name__ == "__main__":
    unittest.main()
