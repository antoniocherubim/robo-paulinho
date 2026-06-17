import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.documents.composite_region_detection import (
    COMPOSITION_CONNECTED,
    COMPOSITION_SINGLE_EXISTING,
    DETECTION_STRATEGY,
    REJECT_FILL_RATIO_BELOW_MIN,
    REJECT_SINGLE_CELL_COMPONENT,
    ParametrosRegioesCompostas,
    _bbox_chave,
    celulas_sao_adjacentes,
    coletar_celulas_base,
    detectar_componentes_celulas,
    detectar_regioes_compostas_documento,
    detectar_regioes_compostas_pagina,
    salvar_regioes_compostas,
)
from nbr12721.documents.region_detection import (
    REJECT_AREA_ABOVE_PAGE_RATIO,
    REJECT_AREA_BELOW_MIN,
    REJECT_HEIGHT_BELOW_MIN,
    REJECT_WIDTH_BELOW_MIN,
)
from nbr12721.settings.config import PASTA_SAIDA


def _bbox(x0, top, x1, bottom) -> dict:
    width = x1 - x0
    height = bottom - top
    return {
        "x0": x0,
        "top": top,
        "x1": x1,
        "bottom": bottom,
        "width": width,
        "height": height,
        "area_pdf_units": width * height,
    }


def _regiao(
    rid: str,
    x0: float,
    top: float,
    x1: float,
    bottom: float,
    *,
    confidence: str = "candidate",
    rejection_reason: str = "",
) -> dict:
    bbox = _bbox(x0, top, x1, bottom)
    return {
        "id": rid,
        "bbox": bbox,
        "centroid": {"x": (x0 + x1) / 2, "y": (top + bottom) / 2},
        "confidence": confidence,
        "rejection_reason": rejection_reason,
    }


def _pagina_regioes(
    regions: list[dict] | None = None,
    rejected_regions: list[dict] | None = None,
    *,
    width: float = 1000,
    height: float = 1000,
    page_number: int = 1,
) -> dict:
    return {
        "page_number": page_number,
        "width": width,
        "height": height,
        "coordinate_system": "pdfplumber_top_left_points",
        "regions": regions or [],
        "rejected_regions": rejected_regions or [],
    }


def _doc_regioes(pages: list[dict], *, file_name: str = "teste.pdf") -> dict:
    return {
        "source": "test",
        "file_name": file_name,
        "pages": pages,
    }


class TestCompositeRegionDetection(unittest.TestCase):
    def test_coleta_inclui_regions_e_rejeitadas_elegiveis(self):
        pagina = _pagina_regioes(
            regions=[_regiao("p001_r0001", 0, 0, 50, 50)],
            rejected_regions=[
                _regiao("p001_x0001", 60, 0, 80, 20, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
                _regiao("p001_x0002", 90, 0, 500, 500, confidence="rejected", rejection_reason=REJECT_AREA_ABOVE_PAGE_RATIO),
            ],
        )
        celulas = coletar_celulas_base(pagina)
        self.assertEqual(len(celulas), 2)
        self.assertTrue(any(c["was_accepted_region"] for c in celulas))
        self.assertTrue(any(not c["was_accepted_region"] for c in celulas))

    def test_adjacencia_horizontal_e_vertical(self):
        params = ParametrosRegioesCompostas(adjacency_tolerance=3.0)
        a = {"bbox": _bbox(0, 0, 50, 50)}
        b = {"bbox": _bbox(50, 0, 100, 50)}
        c = {"bbox": _bbox(0, 50, 50, 100)}
        self.assertTrue(celulas_sao_adjacentes(a, b, params))
        self.assertTrue(celulas_sao_adjacentes(a, c, params))
        self.assertFalse(celulas_sao_adjacentes(b, c, params))

    def test_duas_celulas_adjacentes_formam_componente_conectado(self):
        pagina = _pagina_regioes(
            rejected_regions=[
                _regiao("p001_x0001", 0, 0, 50, 50, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
                _regiao("p001_x0002", 50, 0, 120, 50, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
            ],
        )
        params = ParametrosRegioesCompostas(
            min_composite_width=20,
            min_composite_height=20,
            min_composite_area=100,
            min_fill_ratio=0.05,
        )
        resultado = detectar_regioes_compostas_pagina(pagina, params)
        self.assertEqual(resultado["stats"]["base_cells"], 2)
        self.assertEqual(resultado["stats"]["components_found"], 1)
        self.assertEqual(len(resultado["composite_regions"]), 1)
        comp = resultado["composite_regions"][0]
        self.assertEqual(comp["cell_count"], 2)
        self.assertEqual(comp["composition_type"], COMPOSITION_CONNECTED)
        self.assertEqual(comp["adjacency_edge_count"], 1)
        self.assertIn("rejected", comp["source_confidences"])

    def test_singleton_de_regions_recebe_single_existing_region(self):
        pagina = _pagina_regioes(
            regions=[_regiao("p001_r0001", 100, 100, 200, 200)],
        )
        params = ParametrosRegioesCompostas(
            min_composite_width=20,
            min_composite_height=20,
            min_composite_area=100,
        )
        resultado = detectar_regioes_compostas_pagina(pagina, params)
        self.assertEqual(len(resultado["composite_regions"]), 1)
        comp = resultado["composite_regions"][0]
        self.assertEqual(comp["composition_type"], COMPOSITION_SINGLE_EXISTING)
        self.assertEqual(comp["cell_count"], 1)
        self.assertIn("candidate", comp["source_confidences"])

    def test_singleton_so_rejeitada_eh_rejeitada(self):
        pagina = _pagina_regioes(
            rejected_regions=[
                _regiao("p001_x0001", 0, 0, 50, 50, confidence="rejected", rejection_reason=REJECT_AREA_BELOW_MIN),
            ],
        )
        params = ParametrosRegioesCompostas(min_composite_area=100)
        resultado = detectar_regioes_compostas_pagina(pagina, params)
        self.assertEqual(len(resultado["composite_regions"]), 0)
        self.assertEqual(len(resultado["rejected_composite_regions"]), 1)
        self.assertEqual(
            resultado["rejected_composite_regions"][0]["rejection_reason"],
            REJECT_SINGLE_CELL_COMPONENT,
        )

    def test_fill_ratio_abaixo_do_minimo_rejeita(self):
        pagina = _pagina_regioes(
            rejected_regions=[
                _regiao("p001_x0001", 0, 0, 30, 10, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
                _regiao("p001_x0002", 0, 10, 10, 20, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
            ],
        )
        params = ParametrosRegioesCompostas(
            adjacency_tolerance=3.0,
            min_composite_width=20,
            min_composite_height=20,
            min_composite_area=100,
            min_fill_ratio=0.70,
        )
        resultado = detectar_regioes_compostas_pagina(pagina, params)
        self.assertEqual(len(resultado["composite_regions"]), 0)
        self.assertEqual(len(resultado["rejected_composite_regions"]), 1)
        self.assertEqual(
            resultado["rejected_composite_regions"][0]["rejection_reason"],
            REJECT_FILL_RATIO_BELOW_MIN,
        )

    def test_source_confidences_preservadas_em_mistura(self):
        pagina = _pagina_regioes(
            regions=[_regiao("p001_r0001", 0, 0, 50, 50)],
            rejected_regions=[
                _regiao("p001_x0001", 50, 0, 120, 50, confidence="rejected", rejection_reason=REJECT_WIDTH_BELOW_MIN),
            ],
        )
        params = ParametrosRegioesCompostas(
            min_composite_width=20,
            min_composite_height=20,
            min_composite_area=100,
        )
        resultado = detectar_regioes_compostas_pagina(pagina, params)
        comp = resultado["composite_regions"][0]
        self.assertEqual(sorted(comp["source_confidences"]), ["candidate", "rejected"])

    def test_dedup_por_bbox_usa_adjacency_tolerance(self):
        bbox = _bbox(10, 10, 110, 110)
        chave_a = _bbox_chave(bbox, 3.0)
        chave_b = _bbox_chave({**bbox, "x0": 10.5, "top": 10.5}, 3.0)
        self.assertEqual(chave_a, chave_b)

    def test_stats_registram_pair_checks_e_adjacency_edges(self):
        celulas = [
            {"id": "a", "bbox": _bbox(0, 0, 50, 50), "original_confidence": "rejected", "original_rejection_reason": REJECT_WIDTH_BELOW_MIN, "was_accepted_region": False},
            {"id": "b", "bbox": _bbox(50, 0, 100, 50), "original_confidence": "rejected", "original_rejection_reason": REJECT_WIDTH_BELOW_MIN, "was_accepted_region": False},
            {"id": "c", "bbox": _bbox(200, 200, 250, 250), "original_confidence": "rejected", "original_rejection_reason": REJECT_WIDTH_BELOW_MIN, "was_accepted_region": False},
        ]
        componentes, adj, edges, pair_checks = detectar_componentes_celulas(celulas)
        self.assertEqual(pair_checks, 3)
        self.assertEqual(edges, 1)
        self.assertEqual(len(componentes), 2)

    def test_salvar_grava_json_valido(self):
        doc = _doc_regioes([_pagina_regioes(regions=[_regiao("p001_r0001", 50, 50, 150, 150)])])
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "teste.regioes_compostas.json"
            resultado = salvar_regioes_compostas(doc, destino)
            self.assertTrue(destino.is_file())
            carregado = json.loads(destino.read_text(encoding="utf-8"))
            self.assertEqual(carregado["pages"][0]["detection_strategy"], DETECTION_STRATEGY)
            self.assertEqual(resultado["page_count"], 1)

    def test_integracao_real_torre01_se_disponivel(self):
        pasta = Path(PASTA_SAIDA) / "geometria_regioes"
        arquivos = sorted(pasta.glob("*.regioes.json"))
        if not arquivos:
            self.skipTest("Nenhum *.regioes.json em geometria_regioes")
        doc = json.loads(arquivos[0].read_text(encoding="utf-8"))
        resultado = detectar_regioes_compostas_documento(doc)
        total_base = sum(p["stats"]["base_cells"] for p in resultado["pages"])
        self.assertGreater(total_base, 0)
        for pagina in resultado["pages"]:
            stats = pagina["stats"]
            self.assertIn("pair_checks", stats)
            self.assertIn("adjacency_edges", stats)
            self.assertIn("components_found", stats)
            for comp in pagina["composite_regions"]:
                self.assertIn("adjacency_edge_count", comp)
                self.assertIn("source_confidences", comp)
                self.assertIn("composition_type", comp)
                self.assertIn("fill_ratio", comp)


if __name__ == "__main__":
    unittest.main()
