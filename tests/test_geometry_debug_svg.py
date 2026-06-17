import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.tools.geometry_debug_svg import (
    LimitesCamada,
    gerar_svg_pagina,
    gerar_svgs_inventario,
    salvar_svgs_inventario,
)


def _inventario_minimo() -> dict:
    return {
        "source": "/tmp/exemplo.pdf",
        "file_name": "exemplo.geometria.json",
        "page_count": 1,
        "pages": [
            {
                "page_number": 1,
                "width": 100,
                "height": 100,
                "coordinate_system": "pdfplumber_top_left_points",
                "stats": {"texts": 1, "lines": 3, "rects": 1, "curves": 1},
                "texts": [
                    {
                        "text": "BWC",
                        "x0": 10,
                        "top": 20,
                        "x1": 30,
                        "bottom": 28,
                    }
                ],
                "lines": [
                    {
                        "x0": 0,
                        "top": 50,
                        "x1": 100,
                        "bottom": 50,
                        "orientation": "horizontal",
                    },
                    {
                        "x0": 50,
                        "top": 0,
                        "x1": 50,
                        "bottom": 100,
                        "orientation": "vertical",
                    },
                    {
                        "x0": 0,
                        "top": 0,
                        "x1": 100,
                        "bottom": 100,
                        "orientation": "diagonal",
                    },
                ],
                "rects": [
                    {
                        "x0": 5,
                        "top": 5,
                        "width": 20,
                        "height": 15,
                    }
                ],
                "curves": [
                    {
                        "x0": 60,
                        "top": 60,
                        "width": 10,
                        "height": 10,
                    }
                ],
            }
        ],
    }


class TestGeometryDebugSvg(unittest.TestCase):
    def test_gerar_svg_minimo_contem_elementos_e_classes(self):
        inventario = _inventario_minimo()
        pagina = inventario["pages"][0]
        svg = gerar_svg_pagina(pagina, inventario=inventario)

        self.assertIn("<svg", svg)
        self.assertIn('viewBox="0 0 100', svg)
        self.assertIn("BWC", svg)
        self.assertIn('id="layer-rects"', svg)
        self.assertIn('id="layer-curves"', svg)
        self.assertIn('id="layer-lines"', svg)
        self.assertIn('id="layer-texts"', svg)
        self.assertIn('id="layer-legend"', svg)
        self.assertIn("geo-line-horizontal", svg)
        self.assertIn("geo-line-vertical", svg)
        self.assertIn("geo-line-diagonal", svg)
        self.assertIn("geo-rect", svg)
        self.assertIn("geo-curve", svg)
        self.assertIn("geo-text", svg)
        self.assertIn("<metadata>", svg)
        self.assertIn("pdfplumber_top_left_points", svg)
        self.assertIn("/tmp/exemplo.pdf", svg)

    def test_trunca_texto_visual_preserva_title(self):
        inventario = _inventario_minimo()
        pagina = inventario["pages"][0]
        texto_longo = "LAMINADODEMADEIRA_EXTRA_LONGO"
        pagina["texts"] = [
            {
                "text": texto_longo,
                "x0": 1,
                "top": 2,
                "x1": 10,
                "bottom": 8,
            }
        ]
        svg = gerar_svg_pagina(pagina, inventario=inventario)

        self.assertIn(f"<title>{texto_longo}</title>", svg)
        self.assertIn("LAMINADODEMADEIRA...</text>", svg)
        self.assertNotIn(f">{texto_longo}</text>", svg)

    def test_limites_por_camada(self):
        inventario = _inventario_minimo()
        pagina = inventario["pages"][0]
        pagina["lines"] = pagina["lines"] * 3
        pagina["texts"] = pagina["texts"] * 4
        pagina["curves"] = pagina["curves"] * 5

        svg = gerar_svg_pagina(
            pagina,
            inventario=inventario,
            limites=LimitesCamada(max_lines=2, max_curves=1, max_texts=1),
        )

        self.assertEqual(svg.count('class="geo-line-horizontal"'), 1)
        self.assertEqual(svg.count('class="geo-line-vertical"'), 1)
        self.assertEqual(svg.count('class="geo-line-diagonal"'), 0)
        self.assertEqual(svg.count('class="geo-curve"'), 1)
        self.assertEqual(svg.count('class="geo-text"'), 1)

    def test_salvar_svgs_inventario_nome_previsivel(self):
        inventario = _inventario_minimo()
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = salvar_svgs_inventario(inventario, tmpdir, stem="exemplo")
            self.assertEqual(len(caminhos), 1)
            self.assertEqual(caminhos[0].name, "exemplo.p001.debug.svg")
            conteudo = caminhos[0].read_text(encoding="utf-8")
            self.assertIn("<svg", conteudo)

    def test_gerar_svgs_inventario_multiplas_paginas(self):
        inventario = _inventario_minimo()
        inventario["pages"].append({**inventario["pages"][0], "page_number": 2})
        svgs = gerar_svgs_inventario(inventario)
        self.assertEqual([n for n, _ in svgs], [1, 2])

    def test_svg_real_tipo_contem_bwc(self):
        json_path = Path(
            "data/output/saida/geometria_pdf/"
            "AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.geometria.json"
        )
        if not json_path.exists():
            pdf_path = Path("data/input/documentos/AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.pdf")
            if not pdf_path.exists():
                self.skipTest("Fixture de prancha tipo indisponivel")
            try:
                from nbr12721.documents.pdf_geometry import inventariar_pdf

                inventario = inventariar_pdf(pdf_path, max_paginas=1)
            except RuntimeError as exc:
                self.skipTest(str(exc))
        else:
            inventario = json.loads(json_path.read_text(encoding="utf-8"))

        svg = gerar_svg_pagina(inventario["pages"][0], inventario=inventario)
        self.assertIn("BWC", svg)
        textos_pagina = {t["text"] for t in inventario["pages"][0]["texts"]}
        self.assertIn("BWC", textos_pagina)


if __name__ == "__main__":
    unittest.main()
