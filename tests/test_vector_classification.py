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
    REASON_TITLEBLOCK_SUSPECT,
    ParametrosClassificacao,
    classificar_inventario,
    classificar_pagina,
    salvar_classificacao,
)


def _linha(
    x0: float,
    top: float,
    x1: float,
    bottom: float,
    orientation: str,
    length: float | None = None,
) -> dict:
    item = {
        "x0": x0,
        "top": top,
        "x1": x1,
        "bottom": bottom,
        "orientation": orientation,
        "cx": (x0 + x1) / 2,
        "cy": (top + bottom) / 2,
    }
    if length is not None:
        item["length"] = length
    else:
        item["length"] = ((x1 - x0) ** 2 + (bottom - top) ** 2) ** 0.5
    return item


def _pagina_base(linhas: list[dict], textos: list[dict] | None = None, rects: list[dict] | None = None) -> dict:
    return {
        "page_number": 1,
        "width": 1000,
        "height": 1000,
        "coordinate_system": "pdfplumber_top_left_points",
        "texts": textos or [],
        "lines": linhas,
        "rects": rects or [],
        "curves": [],
        "stats": {"texts": len(textos or []), "lines": len(linhas), "rects": len(rects or []), "curves": 0},
    }


class TestVectorClassification(unittest.TestCase):
    def test_horizontal_longa_centro_vira_wall_candidate(self):
        pagina = _pagina_base([_linha(100, 500, 900, 500, "horizontal")])
        resultado = classificar_pagina(pagina)
        walls = resultado["classified"]["wall_candidates"]
        self.assertEqual(len(walls), 1)
        self.assertEqual(walls[0]["classification_reason"], REASON_AXIS_ALIGNED_LONG)
        self.assertEqual(walls[0]["orientation"], "horizontal")
        self.assertEqual(walls[0]["x0"], 100)

    def test_vertical_longa_centro_vira_wall_candidate(self):
        pagina = _pagina_base([_linha(500, 100, 500, 900, "vertical")])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["wall_candidates"]), 1)

    def test_linha_curta_vira_short_noise(self):
        pagina = _pagina_base([_linha(100, 100, 105, 100, "horizontal", length=5)])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["short_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["short_noise"][0]["classification_reason"],
            REASON_LENGTH_BELOW_MIN,
        )

    def test_ponto_vira_thin_noise(self):
        pagina = _pagina_base([_linha(100, 100, 100, 100, "ponto", length=0)])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["thin_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["thin_noise"][0]["classification_reason"],
            REASON_ORIENTATION_POINT,
        )

    def test_comprimento_quase_zero_vira_thin_noise(self):
        pagina = _pagina_base([_linha(100, 100, 100.2, 100.1, "horizontal", length=0.2)])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["thin_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["thin_noise"][0]["classification_reason"],
            REASON_LENGTH_NEAR_ZERO,
        )

    def test_diagonal_vira_diagonal_segments(self):
        pagina = _pagina_base([_linha(0, 0, 100, 100, "diagonal")])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["diagonal_segments"]), 1)
        self.assertEqual(
            resultado["classified"]["diagonal_segments"][0]["classification_reason"],
            REASON_ORIENTATION_DIAGONAL,
        )

    def test_inferior_direita_forte_vira_titleblock(self):
        pagina = _pagina_base([_linha(800, 800, 950, 800, "horizontal")])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["titleblock_or_legend_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["titleblock_or_legend_noise"][0]["classification_reason"],
            REASON_TITLEBLOCK_STRONG,
        )
        self.assertEqual(len(resultado["classified"]["wall_candidates"]), 0)

    def test_margem_inferior_sem_densidade_pode_ser_contorno(self):
        pagina = _pagina_base([_linha(200, 800, 700, 800, "horizontal")])
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["wall_candidates"]), 1)

    def test_margem_suspeita_com_textos_vira_titleblock(self):
        textos = [
            {"text": f"T{i}", "x0": 820 + i, "top": 400, "cx": 820 + i, "cy": 400}
            for i in range(5)
        ]
        pagina = _pagina_base([_linha(800, 400, 950, 400, "horizontal")], textos=textos)
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["titleblock_or_legend_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["titleblock_or_legend_noise"][0]["classification_reason"],
            REASON_TITLEBLOCK_SUSPECT,
        )

    def test_densidade_texto_vira_text_nearby_noise(self):
        textos = [
            {"text": f"T{i}", "x0": 300 + i * 2, "top": 500, "cx": 300 + i * 2, "cy": 500}
            for i in range(6)
        ]
        pagina = _pagina_base([_linha(100, 500, 900, 500, "horizontal")], textos=textos)
        resultado = classificar_pagina(pagina)
        self.assertEqual(len(resultado["classified"]["text_nearby_noise"]), 1)
        self.assertEqual(
            resultado["classified"]["text_nearby_noise"][0]["classification_reason"],
            REASON_NEAR_TEXT_DENSITY,
        )

    def test_axis_aligned_segments_e_rollup_nao_exclusivo(self):
        linha_centro = _linha(100, 500, 900, 500, "horizontal")
        linha_carimbo = _linha(800, 800, 950, 800, "horizontal")
        pagina = _pagina_base([linha_centro, linha_carimbo])
        resultado = classificar_pagina(pagina)

        self.assertEqual(len(resultado["classified"]["wall_candidates"]), 1)
        self.assertEqual(len(resultado["classified"]["titleblock_or_legend_noise"]), 1)
        self.assertEqual(len(resultado["classified"]["axis_aligned_segments"]), 2)
        self.assertEqual(
            resultado["classified"]["axis_aligned_segments"][1]["exclusive_bucket"],
            "titleblock_or_legend_noise",
        )

    def test_stats_separam_exclusivo_e_rollup(self):
        pagina = _pagina_base(
            [
                _linha(100, 500, 900, 500, "horizontal"),
                _linha(800, 800, 950, 800, "horizontal"),
                _linha(0, 0, 5, 0, "horizontal", length=5),
            ]
        )
        stats = classificar_pagina(pagina)["stats"]
        self.assertEqual(stats["input_lines"], 3)
        self.assertEqual(stats["exclusive_classified_lines"], 3)
        self.assertEqual(stats["wall_candidates"], 1)
        self.assertEqual(stats["discarded_noise"], 2)
        self.assertEqual(stats["axis_aligned_segments"], 2)
        self.assertEqual(stats["wall_candidates"] + stats["discarded_noise"], stats["input_lines"])

    def test_salvar_classificacao_grava_json(self):
        inventario = {
            "source": "/tmp/x.pdf",
            "file_name": "x.pdf",
            "pages": [_pagina_base([_linha(100, 500, 900, 500, "horizontal")])],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            destino = Path(tmpdir) / "x.classificada.json"
            salvar_classificacao(inventario, destino)
            payload = json.loads(destino.read_text(encoding="utf-8"))
        self.assertIn("classification_params", payload)
        self.assertIn("wall_candidates", payload["pages"][0]["classified"])

    def test_integracao_prancha_tipo_volume_plausivel(self):
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

        resultado = classificar_inventario(inventario)
        stats = resultado["pages"][0]["stats"]
        self.assertGreater(stats["wall_candidates"], 100)
        self.assertGreater(stats["discarded_noise"], 0)
        self.assertLess(stats["wall_candidates"], stats["input_lines"])
        self.assertGreaterEqual(stats["axis_aligned_segments"], stats["wall_candidates"])


if __name__ == "__main__":
    unittest.main()
