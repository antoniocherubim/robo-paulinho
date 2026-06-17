import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.tools.region_debug_svg import (
    LimitesRegioesSvg,
    _escape_xml,
    _label_curto,
    gerar_svg_pagina_regioes,
    gerar_svgs_regioes,
    salvar_svgs_regioes,
)


def _regiao(
    region_id: str,
    *,
    confidence: str,
    rejection_reason: str = "",
    x0: float = 100,
    top: float = 200,
    width: float = 150,
    height: float = 150,
) -> dict:
    x1 = x0 + width
    bottom = top + height
    return {
        "id": region_id,
        "bbox": {
            "x0": x0,
            "top": top,
            "x1": x1,
            "bottom": bottom,
            "width": width,
            "height": height,
            "area_pdf_units": width * height,
        },
        "centroid": {"x": x0 + width / 2, "y": top + height / 2},
        "edges": {
            "top": {"pos": top, "start": x0, "end": x1, "source_indices": [0, 1], "source_count": 2},
            "right": {"pos": x1, "start": top, "end": bottom, "source_indices": [2], "source_count": 1},
            "bottom": {"pos": bottom, "start": x0, "end": x1, "source_indices": [3, 4], "source_count": 2},
            "left": {"pos": x0, "start": top, "end": bottom, "source_indices": [5], "source_count": 1},
        },
        "source": "orthogonal_cell_from_wall_candidates",
        "confidence": confidence,
        "rejection_reason": rejection_reason,
    }


def _regioes_doc_minimo() -> dict:
    return {
        "source": "/tmp/exemplo.pdf",
        "file_name": "exemplo.regioes.json",
        "pages": [
            {
                "page_number": 1,
                "width": 1000,
                "height": 1000,
                "coordinate_system": "pdfplumber_top_left_points",
                "detection_strategy": "adjacent_grid_v1",
                "truncated": False,
                "regions": [
                    _regiao("p001_r0001", confidence="candidate"),
                ],
                "rejected_regions": [
                    _regiao(
                        "p001_x0001",
                        confidence="rejected",
                        rejection_reason="area_below_min",
                        x0=400,
                        top=400,
                        width=20,
                        height=20,
                    ),
                ],
                "stats": {
                    "grid_cells_checked": 10,
                    "closed_cells_found": 2,
                    "candidate_regions": 1,
                    "rejected_regions": 1,
                    "rejected_regions_saved": 1,
                    "duplicate_regions": 0,
                },
            }
        ],
    }


class TestRegionDebugSvg(unittest.TestCase):
    def test_label_curto(self):
        self.assertEqual(_label_curto("p001_r0001"), "r0001")
        self.assertEqual(_label_curto("p001_x0042"), "x0042")

    def test_svg_contem_camadas_e_classes(self):
        doc = _regioes_doc_minimo()
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc)
        self.assertIn("<svg", svg)
        self.assertIn('id="layer-regions"', svg)
        self.assertIn('id="layer-rejected-regions"', svg)
        self.assertIn('id="layer-centroids"', svg)
        self.assertIn('id="layer-labels"', svg)
        self.assertIn("cls-region", svg)
        self.assertIn("cls-rejected", svg)

    def test_title_contem_id_completo_e_edge_source_counts(self):
        doc = _regioes_doc_minimo()
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc)
        self.assertIn("id=p001_r0001", svg)
        self.assertIn("edge_source_counts=top:2,right:1,bottom:2,left:1", svg)
        self.assertIn("rejection_reason=area_below_min", svg)

    def test_labels_curtos_sem_id_completo_no_texto(self):
        doc = _regioes_doc_minimo()
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc)
        self.assertIn(">r0001</text>", svg)
        self.assertIn(">x0001</text>", svg)
        self.assertNotIn(">p001_r0001</text>", svg)

    def test_ocultar_labels_mantem_centroides(self):
        doc = _regioes_doc_minimo()
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc, mostrar_labels=False)
        self.assertNotIn('id="layer-labels"', svg)
        self.assertIn('id="layer-centroids"', svg)
        self.assertIn("cls-centroid", svg)

    def test_ocultar_rejeitadas(self):
        doc = _regioes_doc_minimo()
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc, mostrar_rejeitadas=False)
        self.assertNotIn('id="layer-rejected-regions"', svg)
        self.assertNotIn(">x0001</text>", svg)

    def test_metadata_render_limits(self):
        doc = _regioes_doc_minimo()
        limites = LimitesRegioesSvg(max_regions=1, max_rejected=1)
        svg = gerar_svg_pagina_regioes(doc["pages"][0], regioes_doc=doc, limites=limites)
        self.assertIn("rendered_regions", svg)
        self.assertIn("rendered_rejected_regions", svg)
        self.assertIn('"max_regions": 1', svg)

    def test_escape_xml(self):
        self.assertEqual(_escape_xml("a&b<c>d"), "a&amp;b&lt;c&gt;d")

    def test_salvar_nome_previsivel(self):
        doc = _regioes_doc_minimo()
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = salvar_svgs_regioes(doc, tmpdir, stem="exemplo")
            self.assertEqual(caminhos[0].name, "exemplo.p001.regioes.debug.svg")

    def test_gerar_svgs_multiplas_paginas(self):
        doc = _regioes_doc_minimo()
        doc["pages"].append({**doc["pages"][0], "page_number": 2})
        svgs = gerar_svgs_regioes(doc)
        self.assertEqual([n for n, _ in svgs], [1, 2])

    def test_integracao_real_gera_svg_com_rejeitadas(self):
        json_path = Path(
            "data/output/saida/geometria_regioes/"
            "AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.regioes.json"
        )
        if not json_path.exists():
            self.skipTest("JSON de regioes real indisponivel")

        doc = json.loads(json_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmpdir:
            caminhos = salvar_svgs_regioes(
                doc,
                tmpdir,
                limites=LimitesRegioesSvg(max_regions=10, max_rejected=10),
            )
            self.assertEqual(len(caminhos), 1)
            svg = caminhos[0].read_text(encoding="utf-8")

        self.assertIn("layer-rejected-regions", svg)
        if doc["pages"][0].get("rejected_regions"):
            self.assertTrue(
                "rejection_reason=" in svg
                or "width_below_min" in svg
                or "area_below_min" in svg
            )


if __name__ == "__main__":
    unittest.main()
