import unittest
from unittest.mock import MagicMock, patch

from nbr12721.documents.pdf_processing import (
    _ocr_regioes_pagina,
    iterar_texto_pdf_paginas,
    prefiltrar_texto,
)


class TestPrefiltrarTexto(unittest.TestCase):
    def test_preserva_evidencias_criticas_e_limita_tamanho(self):
        texto = """
========================================
DOCUMENTO: exemplo.pdf
========================================
TERRENO: 8.958,97 M2 ARQUITETO E URBANISTA - CAU A30683-9
CURITIBA-PR 24/07/2023 (MAX: 80%)
TOTAL DE VAGAS NO PAVIMENTO 73 VAGAS + 2 VAGAS PNE
(12º AO 202) PAV. TIPO - 65,985 X 80 APTOS 5.278,80
Nº de ALVARÁ: 2457/2023
""" + "\n".join("240x480 240x480 240x480" for _ in range(200))

        filtrado = prefiltrar_texto(texto, verbose=False)

        self.assertLessEqual(len(filtrado), 16000)
        self.assertIn("EVIDENCIAS CRITICAS", filtrado)
        self.assertIn("CURITIBA-PR", filtrado)
        self.assertIn("80 APTOS", filtrado)
        self.assertIn("TOTAL DE VAGAS", filtrado)
        self.assertIn("ALVARÁ: 2457/2023", filtrado)

    def test_prefiltro_preserva_cnpj_colado_sem_barra(self):
        ruido = "\n".join("240x480 240x480 JANELA PORTA" for _ in range(120))
        texto = f"""
========================================
DOCUMENTO: memorial.pdf
========================================
YTICON CONSTRUÇÃO E INCORPORAÇÃO LTDA 06020259103960001
CNPJ10.910.7480001-85
CURITIBA-PR 24/07/2023
{ruido}
"""
        filtrado = prefiltrar_texto(texto, verbose=False)
        self.assertIn("CNPJ10.910.7480001-85", filtrado)

    def test_prefiltro_preserva_linhas_candidatos_quadro8(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_EVIDENCIAS_ACABAMENTOS,
            extrair_candidatos_acabamentos,
        )
        from nbr12721.extraction.deterministic_extraction.extractor import (
            extrair_dados_deterministico,
        )

        ruido = "\n".join("240x480 240x480 JANELA PORTA" for _ in range(120))
        texto = f"""
========================================
DOCUMENTO: memorial.pdf
========================================
{ruido}
CIRC. LAMINADO
ESCADA VAZIODUTO CIMENTADO
BARRILETE PISO CIMENTADO
{ruido}
"""
        filtrado = prefiltrar_texto(texto, verbose=False)
        self.assertIn(MARCADOR_EVIDENCIAS_ACABAMENTOS, filtrado)
        self.assertIn("ESCADA VAZIODUTO CIMENTADO", filtrado)
        self.assertIn("CIRC. LAMINADO", filtrado)

        candidatos = extrair_candidatos_acabamentos(filtrado)
        self.assertGreaterEqual(len(candidatos), 2)
        deps = {c["dependencia"] for c in candidatos if c["quadro"] == "quadro8"}
        self.assertIn("Escada", deps)
        self.assertIn("Circ.", deps)

        dados = extrair_dados_deterministico(filtrado)
        deps_q8 = {
            item["dependencia"]
            for item in dados["quadro8"]["acabamentos"]
            if item.get("dependencia")
        }
        self.assertIn("Escada", deps_q8)
        self.assertIn("Circ.", deps_q8)

    def test_extrai_candidatos_equipamentos_elevador(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_equipamentos

        candidatos = extrair_candidatos_equipamentos("ELEVADOR01 ELEVADOR02")
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["nome"], "Elevador")
        self.assertIn("ELEVADOR01", candidatos[0]["detalhes"])
        self.assertIn("ELEVADOR02", candidatos[0]["detalhes"])

    def test_candidatos_equipamentos_nao_usa_hall_elevador(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_equipamentos

        candidatos = extrair_candidatos_equipamentos("HALL ELEVADOR PISO PORCELANATO")
        self.assertEqual(candidatos, [])

    def test_extrai_candidatos_bomba_recalque(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_equipamentos

        candidatos = extrair_candidatos_equipamentos("BOMBA RECALQUE")
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["nome"], "Bomba de recalque")

    def test_candidatos_equipamentos_rejeita_elevador_area_e_admin(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_equipamentos

        for linha in (
            "ELEVADOR 15,59m²",
            "DATA PROCEDIMENTO VAZIO ELEVADOR 24072023 ENTREGA-R00",
        ):
            with self.subTest(linha=linha):
                self.assertEqual(extrair_candidatos_equipamentos(linha), [])

    def test_quadro6_agrega_linhas_repetidas_ocr(self):
        from nbr12721.extraction.deterministic_extraction.extractor import (
            extrair_dados_deterministico,
        )

        texto = "\n".join(
            [
                "O DEP. DE LIXO, DEP. GÁS E PORTARIA 02 SÃO A TÍTULO PRECÁRIO",
                "ODEP. DE LIXO, DEP. GÁS E PORTARIA 02 SÃO A TÍTULO PRECÁRIO",
                "ELEVADOR01 ELEVADOR02",
                "ELEVADOR03 09 10 11",
                "VAZIO VAZIO ELEVADOR01 ELEVADOR02",
            ]
        )
        dados = extrair_dados_deterministico(texto)
        gas = [i for i in dados["quadro6"]["equipamentos"] if i["nome"] == "Instalação de gás"]
        elev = [i for i in dados["quadro6"]["equipamentos"] if i["nome"] == "Elevador"]
        self.assertEqual(len(gas), 1)
        self.assertEqual(len(elev), 1)
        self.assertIn("ELEVADOR01/ELEVADOR02/ELEVADOR03", elev[0]["detalhes"])

    def test_prefiltro_preserva_linhas_candidatos_quadro6(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_EVIDENCIAS_EQUIPAMENTOS,
            extrair_candidatos_equipamentos,
        )
        from nbr12721.extraction.deterministic_extraction.extractor import (
            extrair_dados_deterministico,
        )

        ruido = "\n".join("240x480 240x480 JANELA PORTA" for _ in range(120))
        texto = f"""
========================================
DOCUMENTO: memorial.pdf
========================================
{ruido}
ELEVADOR01 ELEVADOR02
{ruido}
"""
        filtrado = prefiltrar_texto(texto, verbose=False)
        self.assertIn(MARCADOR_EVIDENCIAS_EQUIPAMENTOS, filtrado)
        self.assertIn("ELEVADOR01", filtrado)

        candidatos = extrair_candidatos_equipamentos(filtrado)
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["nome"], "Elevador")

        dados = extrair_dados_deterministico(filtrado)
        elevadores = [
            i for i in dados["quadro6"]["equipamentos"] if i.get("nome") == "Elevador"
        ]
        self.assertEqual(len(elevadores), 1)
        self.assertIn("ELEVADOR01", elevadores[0]["detalhes"])

    def test_extrai_evidencias_acabamentos_equipamentos(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_EVIDENCIAS_VI_VIII,
            MARCADOR_QUADRO_VI,
            MARCADOR_QUADRO_VIII,
            extrair_evidencias_acabamentos_equipamentos,
        )

        texto = """
DOCUMENTO: memorial.pdf
ELEVADOR01 ELEVADOR02
HALL SOCIAL GOURMET
PISO CIMENTADO
JANELA ALUMINIO ACABAMENTOS COR GRAFITE
240x480 240x480 JANELA PORTA
"""
        resultado = extrair_evidencias_acabamentos_equipamentos(texto)
        self.assertIn(MARCADOR_EVIDENCIAS_VI_VIII, resultado)
        self.assertIn(MARCADOR_QUADRO_VI, resultado)
        self.assertIn(MARCADOR_QUADRO_VIII, resultado)
        self.assertIn("ELEVADOR", resultado)
        self.assertIn("HALL", resultado)

    def test_evidencias_vi_viii_separa_privativo_e_comum(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_QUADRO_VII,
            MARCADOR_QUADRO_VIII,
            extrair_evidencias_acabamentos_equipamentos,
        )

        texto = """
APTO01 SALA PISO PORCELANATO PAREDE PINTURA
SACADA PISO CERAMICA
HALL ELEV. PISO PORCELANATO
ESCADA PISO CIMENTADO
"""
        resultado = extrair_evidencias_acabamentos_equipamentos(texto)
        sec_vii = resultado.split(MARCADOR_QUADRO_VII)[1].split(MARCADOR_QUADRO_VIII)[0]
        sec_viii = resultado.split(MARCADOR_QUADRO_VIII)[1]
        self.assertIn("APTO01", sec_vii)
        self.assertIn("SACADA", sec_vii)
        self.assertNotIn("HALL ELEV", sec_vii)
        self.assertIn("HALL ELEV", sec_viii)
        self.assertIn("ESCADA", sec_viii)
        self.assertNotIn("APTO01", sec_viii)

    def test_evidencias_vi_viii_classifica_elevador_como_quadro6(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_QUADRO_VI,
            MARCADOR_QUADRO_VIII,
            extrair_evidencias_acabamentos_equipamentos,
        )

        texto = """
ELEVADOR01 ELEVADOR02
HALL ELEV. PISO PORCELANATO
"""
        resultado = extrair_evidencias_acabamentos_equipamentos(texto)
        sec_vi = resultado.split(MARCADOR_QUADRO_VI)[1].split(MARCADOR_QUADRO_VIII)[0]
        sec_viii = resultado.split(MARCADOR_QUADRO_VIII)[1]
        self.assertIn("ELEVADOR01", sec_vi)
        self.assertNotIn("HALL ELEV", sec_vi)
        self.assertIn("HALL ELEV", sec_viii)
        self.assertNotIn("ELEVADOR01", sec_viii)

    def test_evidencias_vi_viii_hall_elevador_por_extenso_vai_para_viii(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_QUADRO_VI,
            MARCADOR_QUADRO_VIII,
            extrair_evidencias_acabamentos_equipamentos,
        )

        texto = """
HALL ELEVADOR PISO PORCELANATO
ELEVADOR01 ELEVADOR02
"""
        resultado = extrair_evidencias_acabamentos_equipamentos(texto)
        sec_vi = resultado.split(MARCADOR_QUADRO_VI)[1].split(MARCADOR_QUADRO_VIII)[0]
        sec_viii = resultado.split(MARCADOR_QUADRO_VIII)[1]
        self.assertIn("HALL ELEVADOR", sec_viii)
        self.assertNotIn("HALL ELEVADOR", sec_vi)
        self.assertIn("ELEVADOR01", sec_vi)

    def test_candidato_acabamento_requer_dependencia_e_material(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        self.assertIsNone(_extrair_candidato_acabamento("SACADA", "vii"))
        self.assertIsNone(_extrair_candidato_acabamento("CIMENTADO", "viii"))
        self.assertIsNone(_extrair_candidato_acabamento("PISO PORCELANATO", "vii"))

    def test_material_laminado_de_madeira_colado(self):
        from nbr12721.documents.pdf_processing import _extrair_materiais_linha

        materiais, ctx = _extrair_materiais_linha("SACADA LAMINADODEMADEIRA")
        self.assertIn("Laminado de madeira", materiais)
        self.assertIn("Laminado de madeira", ctx["outros"])

    def test_material_pintura_cor_branco_colado(self):
        from nbr12721.documents.pdf_processing import _extrair_materiais_linha

        materiais, _ctx = _extrair_materiais_linha("BWC PINTURACORBRANCO")
        self.assertIn("Pintura cor branco", materiais)

    def test_candidato_quadro7_estar_jantar_laminado_madeira(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        linha = "ESTARJANTAR 7,74M2 PJ1 LAMINADODEMADEIRA PM1"
        candidato = _extrair_candidato_acabamento(linha, "vii")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["quadro"], "quadro7")
        self.assertEqual(candidato["dependencia"], "Estar/jantar")
        self.assertIn("Laminado de madeira", candidato["materiais"])

    def test_candidato_quadro7_sacada_laminado_madeira(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        candidato = _extrair_candidato_acabamento("SACADA LAMINADODEMADEIRA", "vii")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["quadro"], "quadro7")
        self.assertEqual(candidato["dependencia"], "Sacada")
        self.assertIn("Laminado de madeira", candidato["materiais"])

    def test_candidato_quadro7_bwc_com_contexto(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        candidato = _extrair_candidato_acabamento("BWC PISO PORCELANATO PAREDE PINTURA", "vii")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["dependencia"], "BWC")
        ctx = candidato["materiais_contexto"]
        self.assertEqual(ctx["pisos"], ["Porcelanato"])
        self.assertEqual(ctx["paredes"], ["Pintura"])

    def test_prefiltro_preserva_linhas_candidatos_quadro7(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_EVIDENCIAS_ACABAMENTOS,
            extrair_candidatos_acabamentos,
        )
        from nbr12721.extraction.deterministic_extraction.extractor import (
            extrair_dados_deterministico,
        )

        ruido = "\n".join("240x480 240x480 JANELA PORTA" for _ in range(120))
        linha = "ESTARJANTAR 7,74M2 PJ1 LAMINADODEMADEIRA PM1"
        texto = f"""
========================================
DOCUMENTO: memorial.pdf
========================================
{ruido}
{linha}
{ruido}
"""
        filtrado = prefiltrar_texto(texto, verbose=False)
        self.assertIn(MARCADOR_EVIDENCIAS_ACABAMENTOS, filtrado)
        self.assertIn("ESTARJANTAR", filtrado)
        self.assertIn("LAMINADODEMADEIRA", filtrado)

        candidatos = extrair_candidatos_acabamentos(filtrado)
        deps = {c["dependencia"] for c in candidatos if c["quadro"] == "quadro7"}
        self.assertIn("Estar/jantar", deps)

        dados = extrair_dados_deterministico(filtrado)
        deps_q7 = {
            item["dependencia"]
            for item in dados["quadro7"]["acabamentos"]
            if item.get("dependencia")
        }
        self.assertIn("Estar/jantar", deps_q7)

    def test_candidato_quadro7_rejeita_linha_ambigua(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        self.assertIsNone(
            _extrair_candidato_acabamento("SACADA SALA LAMINADODEMADEIRA", "vii")
        )

    def test_candidato_quadro7_janela_sacada_laminado_madeira(self):
        from nbr12721.documents.pdf_processing import (
            _extrair_candidato_acabamento_quadro7_janela,
            extrair_candidatos_acabamentos,
        )

        candidato = _extrair_candidato_acabamento_quadro7_janela("SACADA", "LAMINADODEMADEIRA")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["quadro"], "quadro7")
        self.assertEqual(candidato["dependencia"], "Sacada")
        self.assertIn("Laminado de madeira", candidato["materiais"])

        candidatos = extrair_candidatos_acabamentos("SACADA\nLAMINADODEMADEIRA")
        q7 = [c for c in candidatos if c["quadro"] == "quadro7"]
        self.assertEqual(len(q7), 1)
        self.assertEqual(q7[0]["dependencia"], "Sacada")

    def test_candidato_quadro7_janela_estar_jantar_laminado(self):
        from nbr12721.documents.pdf_processing import (
            _extrair_candidato_acabamento_quadro7_janela,
            extrair_candidatos_acabamentos,
        )

        linha_mat = "7,74M2 PJ1 LAMINADODEMADEIRA PM1"
        candidato = _extrair_candidato_acabamento_quadro7_janela("ESTARJANTAR", linha_mat)
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["dependencia"], "Estar/jantar")
        self.assertIn("Laminado de madeira", candidato["materiais"])

        texto = f"ESTARJANTAR\n{linha_mat}"
        candidatos = extrair_candidatos_acabamentos(texto)
        q7 = [c for c in candidatos if c["quadro"] == "quadro7"]
        self.assertEqual(len(q7), 1)

    def test_candidato_quadro7_janela_rejeita_multiplos_ambientes(self):
        from nbr12721.documents.pdf_processing import (
            _extrair_candidato_acabamento_quadro7_janela,
        )

        self.assertIsNone(
            _extrair_candidato_acabamento_quadro7_janela("SACADA", "SALA LAMINADODEMADEIRA")
        )
        self.assertIsNone(
            _extrair_candidato_acabamento_quadro7_janela(
                "APTO01 SACADA",
                "APTO02 SALA LAMINADODEMADEIRA",
            )
        )

    def test_candidato_quadro7_janela_rejeita_bwc_com_material_vizinho(self):
        from nbr12721.documents.pdf_processing import (
            _extrair_candidato_acabamento,
            _extrair_candidato_acabamento_quadro7_janela,
        )

        self.assertIsNone(
            _extrair_candidato_acabamento_quadro7_janela(
                "BWC",
                "LAMINADODEMADEIRA 2,70M2",
            )
        )
        candidato = _extrair_candidato_acabamento("BWC CERÂMICA 2,70M2", "vii")
        self.assertIsNotNone(candidato)
        self.assertIn("Ceramica", candidato["materiais"])

    def test_candidato_quadro8_escada_cimentado(self):
        from nbr12721.documents.pdf_processing import (
            MARCADOR_CANDIDATOS_VII_VIII,
            _extrair_candidato_acabamento,
            extrair_candidatos_acabamentos_estruturados,
        )

        linha = "ESCADA VAZIODUTO CIMENTADO"
        candidato = _extrair_candidato_acabamento(linha, "viii")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["quadro"], "quadro8")
        self.assertEqual(candidato["dependencia"], "Escada")
        self.assertIn("Cimentado", candidato["materiais"])

        bloco = extrair_candidatos_acabamentos_estruturados(linha)
        self.assertIn(MARCADOR_CANDIDATOS_VII_VIII, bloco)
        self.assertIn("dependencia=Escada", bloco)
        self.assertIn("materiais=Cimentado", bloco)

    def test_candidato_quadro8_circ_laminado(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        candidato = _extrair_candidato_acabamento("CIRC. LAMINADO", "viii")
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["quadro"], "quadro8")
        self.assertEqual(candidato["dependencia"], "Circ.")
        self.assertEqual(candidato["materiais"], ["Laminado"])

    def test_sacada_sem_material_nao_gera_candidato(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_acabamentos_estruturados

        texto = """
SACADA
ESCADA VAZIODUTO CIMENTADO
"""
        bloco = extrair_candidatos_acabamentos_estruturados(texto)
        self.assertIn("dependencia=Escada", bloco)
        self.assertNotIn("dependencia=Sacada", bloco)

    def test_candidato_sala_com_materiais_contexto(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        candidato = _extrair_candidato_acabamento(
            "APTO01 SALA PISO PORCELANATO PAREDE PINTURA",
            "vii",
        )
        self.assertIsNotNone(candidato)
        self.assertEqual(candidato["dependencia"], "Sala")
        self.assertIn("Porcelanato", candidato["materiais"])
        self.assertIn("Pintura", candidato["materiais"])
        ctx = candidato["materiais_contexto"]
        self.assertIn("Porcelanato", ctx["pisos"])
        self.assertIn("Pintura", ctx["paredes"])

    def test_candidato_rejeita_linha_ambigua_multiplas_dependencias(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        linha = "SACADA PISO CERAMICA SALA PISO PORCELANATO"
        self.assertIsNone(_extrair_candidato_acabamento(linha, "vii"))

    def test_candidato_hall_elevador_com_porcelanato(self):
        from nbr12721.documents.pdf_processing import _extrair_candidato_acabamento

        for linha in (
            "HALL ELEVADOR PISO PORCELANATO",
            "HALL ELEV. PISO PORCELANATO",
        ):
            with self.subTest(linha=linha):
                candidato = _extrair_candidato_acabamento(linha, "viii")
                self.assertIsNotNone(candidato)
                self.assertEqual(candidato["quadro"], "quadro8")
                self.assertEqual(candidato["dependencia"], "Hall elevador")
                self.assertIn("Porcelanato", candidato["materiais"])
                self.assertIn("Porcelanato", candidato["materiais_contexto"]["pisos"])

    def test_extrair_candidatos_acabamentos_retorna_lista(self):
        from nbr12721.documents.pdf_processing import extrair_candidatos_acabamentos

        texto = "ESCADA VAZIODUTO CIMENTADO\nSACADA"
        candidatos = extrair_candidatos_acabamentos(texto)
        self.assertIsInstance(candidatos, list)
        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0]["quadro"], "quadro8")
        self.assertEqual(candidatos[0]["dependencia"], "Escada")


class TestOcrRegional(unittest.TestCase):
    def _imagem_fake(self, largura=1000, altura=800):
        img = MagicMock()
        img.size = (largura, altura)

        def crop(box):
            crop_img = MagicMock()
            crop_img.size = (box[2] - box[0], box[3] - box[1])
            return crop_img

        img.crop = crop
        return img

    def test_ocr_regioes_concatena_marcadores(self):
        img = self._imagem_fake()
        pytesseract = MagicMock()
        pytesseract.image_to_string.side_effect = [
            "AREA TERRENO 6956",
            "CREA PR",
            "ALVARA 123",
        ]

        with patch(
            "nbr12721.documents.pdf_processing._renderizar_pagina",
            return_value=img,
        ):
            texto = _ocr_regioes_pagina(
                MagicMock(), pytesseract, "/tmp/x.pdf", 1, None
            )

        self.assertIn("OCR_REGIAO: direita", texto)
        self.assertIn("OCR_REGIAO: inferior_direita", texto)
        self.assertIn("OCR_REGIAO: inferior", texto)
        self.assertIn("AREA TERRENO", texto)

    def test_ocr_regiao_falha_nao_aborta_demais(self):
        img = self._imagem_fake()
        pytesseract = MagicMock()
        pytesseract.image_to_string.side_effect = [
            RuntimeError("timeout"),
            "texto inferior direita",
            "texto inferior",
        ]

        with patch(
            "nbr12721.documents.pdf_processing._renderizar_pagina",
            return_value=img,
        ):
            texto = _ocr_regioes_pagina(
                MagicMock(), pytesseract, "/tmp/x.pdf", 1, None
            )

        self.assertIn("OCR_REGIAO: inferior_direita", texto)
        self.assertIn("texto inferior direita", texto)

    def test_pagina_grande_full_page_mais_regional(self):
        pagina = MagicMock()
        pagina.width = 2000
        pagina.height = 1000
        pagina.extract_text.return_value = ""

        pdf = MagicMock()
        pdf.pages = [pagina]
        pdf.__enter__ = MagicMock(return_value=pdf)
        pdf.__exit__ = MagicMock(return_value=False)

        with (
            patch("pdfplumber.open", return_value=pdf),
            patch(
                "nbr12721.documents.pdf_processing._pagina_muito_grande",
                return_value=True,
            ),
            patch(
                "nbr12721.documents.pdf_processing.OCR_USAR_ARQUIVOS_TEMP",
                True,
            ),
            patch(
                "nbr12721.documents.pdf_processing._ocr_pagina_com_arquivo_temp",
                return_value="65,985 X 80 APTOS\n22 PAVIMENTOS",
            ) as mock_full,
            patch(
                "nbr12721.documents.pdf_processing._ocr_regioes_pagina",
                return_value="OCR_REGIAO: direita\nÁREA TERRENO [AT] 6.956,97",
            ) as mock_regional,
        ):
            paginas = list(iterar_texto_pdf_paginas("/tmp/grande.pdf"))

        mock_full.assert_called_once()
        mock_regional.assert_called_once()
        self.assertEqual(len(paginas), 1)
        texto = paginas[0][1]
        self.assertIn("80 APTOS", texto)
        self.assertIn("TERRENO", texto)
        self.assertIn("OCR_REGIAO:", texto)


if __name__ == "__main__":
    unittest.main()
