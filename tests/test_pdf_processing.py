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
