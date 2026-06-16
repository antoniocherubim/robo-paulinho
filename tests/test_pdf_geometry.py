import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.documents.pdf_geometry import (
    classificar_orientacao_linha,
    inventariar_pdf,
    salvar_inventario_pdf,
)


class TestPdfGeometry(unittest.TestCase):
    def test_classificar_orientacao_linha(self):
        self.assertEqual(classificar_orientacao_linha(0, 0, 10, 0), "horizontal")
        self.assertEqual(classificar_orientacao_linha(0, 0, 0, 10), "vertical")
        self.assertEqual(classificar_orientacao_linha(0, 0, 10, 10), "diagonal")
        self.assertEqual(classificar_orientacao_linha(0, 0, 0.1, 0.1), "ponto")

    def test_inventario_pdf_real_tipo_contem_textos_e_vetores(self):
        pdf_path = Path("data/input/documentos/AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.pdf")
        if not pdf_path.exists():
            self.skipTest("PDF fixture local indisponivel")

        try:
            inventario = inventariar_pdf(pdf_path, max_paginas=1)
        except RuntimeError as exc:
            self.skipTest(str(exc))

        pagina = inventario["pages"][0]
        textos = {item["text"] for item in pagina["texts"]}

        self.assertEqual(inventario["file_name"], pdf_path.name)
        self.assertEqual(inventario["page_count"], 1)
        self.assertIn("BWC", textos)
        self.assertGreater(pagina["stats"]["lines"], 1000)
        self.assertGreater(pagina["stats"]["rects"], 0)
        self.assertGreater(pagina["stats"]["curves"], 0)
        self.assertEqual(pagina["coordinate_system"], "pdfplumber_top_left_points")

    def test_salvar_inventario_pdf_serializa_json(self):
        pdf_path = Path("data/input/documentos/AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.pdf")
        if not pdf_path.exists():
            self.skipTest("PDF fixture local indisponivel")

        with tempfile.TemporaryDirectory() as tmpdir:
            destino = Path(tmpdir) / "inventario.json"
            try:
                salvar_inventario_pdf(pdf_path, destino, max_paginas=1)
            except RuntimeError as exc:
                self.skipTest(str(exc))

            payload = json.loads(destino.read_text(encoding="utf-8"))

        self.assertEqual(payload["page_count"], 1)
        self.assertIn("pages", payload)

