import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.documents.vector_classification import (
    REASON_AXIS_ALIGNED_LONG,
    REASON_LENGTH_BELOW_MIN,
    REASON_LENGTH_NEAR_ZERO,
    REASON_NEAR_TEXT_DENSITY,
    REASON_ORIENTATION_DIAGONAL,
    REASON_ORIENTATION_POINT,
    REASON_TITLEBLOCK_STRONG,
)
from nbr12721.tools.vector_classification_debug_svg import (
    LimitesClassificacaoSvg,
    _escape_xml,
    gerar_svg_pagina_classificada,
    gerar_svgs_classificacao,
    salvar_svgs_classificacao,
)


def _linha(x0, top, x1, bottom, orientation, reason, length=100.0, exclusive_bucket=None):
    item = {
        "x0": x0,
        "top": top,
        "x1": x1,
        "bottom": bottom,
        "orientation": orientation,
        "length": length,
        "classification_reason": reason,
    }
    if exclusive_bucket:
        item["exclusive_bucket"] = exclusive_bucket
    return item


def _classificacao_minima() -> dict:
    return {
        "source": "/tmp/exemplo.pdf",
        "file_name": "exemplo.classificada.json",
        "classification_params": {"min_length_wall": 10},
        "pages": [
            {
                "page_number": 1,
                "width": 1000,
                "height": 1000,
                "coordinate_system": "pdfplumber_top_left_points",
                "stats": {"wall_candidates": 1},
                "classified": {
                    "wall_candidates": [
                        _linha(100, 500, 900, 500, "horizontal", REASON_AXIS_ALIGNED_LONG)
                    ],
                    "axis_aligned_segments": [
                        _linha(100, 500, 900, 500, "horizontal", REASON_AXIS_ALIGNED_LONG),
                        _linha(
                            800,
                            800,
                            950,
                            800,
                            "horizontal",
                            REASON_TITLEBLOCK_STRONG,
                            exclusive_bucket="titleblock_or_legend_noise",
                        ),
                    ],
                    "diagonal_segments": [
                        _linha(0, 0, 100, 100, "diagonal", REASON_ORIENTATION_DIAGONAL)
                    ],
                    "titleblock_or_legend_noise": [
                        _linha(800, 800, 950, 800, "horizontal", REASON_TITLEBLOCK_STRONG)
                    ],
                    "text_nearby_noise": [
                        _linha(200, 200, 400, 200, "horizontal", REASON_NEAR_TEXT_DENSITY)
                    ],
                    "short_noise": [
                        _linha(10, 10, 15, 10, "horizontal", REASON_LENGTH_BELOW_MIN, length=5)
                    ],
                    "thin_noise": [
                        _linha(20, 20, 20, 20, "ponto", REASON_ORIENTATION_POINT, length=0)
                    ],
                    "rect_candidates": [
                        {
                            "x0": 5,
                            "top": 5,
                            "width": 20,
                            "height": 15,
                            "classification_reason": "rect_outside_titleblock",
                        }
                    ],
                    "curve_candidates": [
                        {
                            "x0": 60,
                            "top": 60,
                            "width": 10,
                            "height": 10,
                            "classification_reason": "curve_outside_titleblock",
                        }
                    ],
                },
            }
        ],
    }


class TestVectorClassificationDebugSvg(unittest.TestCase):
    def test_svg_contem_camadas_e_wall_candidate(self):
        classificacao = _classificacao_minima()
        pagina = classificacao["pages"][0]
        svg = gerar_svg_pagina_classificada(pagina, classificacao=classificacao)

        self.assertIn("<svg", svg)
        for layer in (
            "layer-wall-candidates",
            "layer-diagonal",
            "layer-titleblock-noise",
            "layer-text-nearby-noise",
            "layer-short-noise",
            "layer-thin-noise",
            "layer-rect-candidates",
            "layer-curve-candidates",
            "layer-legend",
        ):
            self.assertIn(layer, svg, layer)
        self.assertIn('class="cls-wall"', svg)
        self.assertIn(REASON_AXIS_ALIGNED_LONG, svg)

    def test_axis_aligned_nao_renderiza_por_default(self):
        classificacao = _classificacao_minima()
        svg = gerar_svg_pagina_classificada(classificacao["pages"][0], classificacao=classificacao)
        self.assertNotIn('id="layer-axis-aligned"', svg)

    def test_axis_aligned_renderiza_com_flag(self):
        classificacao = _classificacao_minima()
        svg = gerar_svg_pagina_classificada(
            classificacao["pages"][0],
            classificacao=classificacao,
            mostrar_axis_aligned=True,
        )
        self.assertIn('id="layer-axis-aligned"', svg)
        self.assertIn('class="cls-axis"', svg)
        self.assertIn("exclusive_bucket=titleblock_or_legend_noise", svg)

    def test_escape_xml_em_title(self):
        classificacao = _classificacao_minima()
        classificacao["pages"][0]["classified"]["wall_candidates"][0]["classification_reason"] = (
            "a&b<c>d"
        )
        svg = gerar_svg_pagina_classificada(classificacao["pages"][0], classificacao=classificacao)
        self.assertIn("a&amp;b&lt;c&gt;d", svg)
        self.assertEqual(_escape_xml("a&b<c>d"), "a&amp;b&lt;c&gt;d")

    def test_salvar_nome_previsivel(self):
        classificacao = _classificacao_minima()
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = salvar_svgs_classificacao(classificacao, tmpdir, stem="exemplo")
            self.assertEqual(len(caminhos), 1)
            self.assertEqual(caminhos[0].name, "exemplo.p001.classificada.debug.svg")

    def test_gerar_svgs_classificacao_multiplas_paginas(self):
        classificacao = _classificacao_minima()
        classificacao["pages"].append({**classificacao["pages"][0], "page_number": 2})
        svgs = gerar_svgs_classificacao(classificacao)
        self.assertEqual([n for n, _ in svgs], [1, 2])

    def test_integracao_json_real_contem_wall_layer(self):
        json_path = Path(
            "data/output/saida/geometria_classificada/"
            "AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.classificada.json"
        )
        if not json_path.exists():
            self.skipTest("JSON classificado real indisponivel")

        classificacao = json.loads(json_path.read_text(encoding="utf-8"))
        svg = gerar_svg_pagina_classificada(
            classificacao["pages"][0],
            classificacao=classificacao,
            limites=LimitesClassificacaoSvg(max_wall_candidates=10, max_noise=10),
        )
        self.assertIn("layer-wall-candidates", svg)
        self.assertIn('class="cls-wall"', svg)
        self.assertGreater(classificacao["pages"][0]["stats"]["wall_candidates"], 0)


if __name__ == "__main__":
    unittest.main()
