import json
import tempfile
import unittest
from pathlib import Path

from nbr12721.documents.region_detection import (
    DETECTION_STRATEGY_V1,
    REJECT_AREA_ABOVE_PAGE_RATIO,
    REJECT_AREA_BELOW_MIN,
    TRUNCATION_MAX_REGIONS,
    ParametrosDeteccaoRegioes,
    _bbox_chave,
    _bbox_celula,
    detectar_regioes_classificacao,
    detectar_regioes_pagina,
    normalizar_segmentos,
    salvar_regioes,
)


def _wall_h(x0: float, x1: float, y: float, idx: int | None = None) -> dict:
    return {
        "x0": x0,
        "x1": x1,
        "top": y,
        "bottom": y,
        "orientation": "horizontal",
        "length": abs(x1 - x0),
        **({"source_index": idx} if idx is not None else {}),
    }


def _wall_v(y0: float, y1: float, x: float, idx: int | None = None) -> dict:
    return {
        "x0": x,
        "x1": x,
        "top": y0,
        "bottom": y1,
        "orientation": "vertical",
        "length": abs(y1 - y0),
        **({"source_index": idx} if idx is not None else {}),
    }


def _pagina_classificada(
    walls: list[dict],
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
        "classified": {"wall_candidates": walls},
    }


def _retangulo_perfeito(left=100, top=200, right=250, bottom=350) -> list[dict]:
    return [
        _wall_h(left, right, top, 0),
        _wall_h(left, right, bottom, 1),
        _wall_v(top, bottom, left, 2),
        _wall_v(top, bottom, right, 3),
    ]


class TestRegionDetection(unittest.TestCase):
    def test_retangulo_perfeito_gera_uma_regiao(self):
        resultado = detectar_regioes_pagina(_pagina_classificada(_retangulo_perfeito()))
        self.assertEqual(len(resultado["regions"]), 1)
        self.assertEqual(resultado["regions"][0]["confidence"], "candidate")
        self.assertEqual(resultado["detection_strategy"], DETECTION_STRATEGY_V1)
        self.assertEqual(resultado["stats"]["closed_cells_found"], 1)

    def test_gap_dentro_snap_gera_regiao(self):
        walls = [
            _wall_h(100, 172, 200, 0),
            _wall_h(174, 250, 200, 1),
            _wall_h(100, 250, 350, 2),
            _wall_v(200, 350, 100, 3),
            _wall_v(200, 350, 250, 4),
        ]
        params = ParametrosDeteccaoRegioes(snap_tolerance=3.0, merge_tolerance=2.0)
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(len(resultado["regions"]), 1)

    def test_gap_acima_snap_nao_gera_regiao(self):
        walls = [
            _wall_h(100, 170, 200, 0),
            _wall_h(180, 250, 200, 1),
            _wall_h(100, 250, 350, 2),
            _wall_v(200, 350, 100, 3),
            _wall_v(200, 350, 250, 4),
        ]
        params = ParametrosDeteccaoRegioes(snap_tolerance=3.0)
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(len(resultado["regions"]), 0)
        self.assertEqual(resultado["stats"]["closed_cells_found"], 0)

    def test_segmentos_colineares_mesclados_geram_regiao(self):
        walls = [
            _wall_h(100, 172, 200, 0),
            _wall_h(174, 250, 200, 1),
            _wall_h(100, 250, 350, 2),
            _wall_v(200, 350, 100, 3),
            _wall_v(200, 350, 250, 4),
        ]
        resultado = detectar_regioes_pagina(_pagina_classificada(walls))
        self.assertEqual(len(resultado["regions"]), 1)
        norm = normalizar_segmentos(_pagina_classificada(walls))
        self.assertEqual(len(norm["horizontal"]), 3)

    def test_area_abaixo_minimo_rejeitada(self):
        walls = _retangulo_perfeito(100, 200, 108, 208)
        params = ParametrosDeteccaoRegioes(min_region_area=100.0)
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(len(resultado["regions"]), 0)
        self.assertEqual(resultado["stats"]["rejected_regions"], 1)
        self.assertEqual(resultado["rejected_regions"][0]["rejection_reason"], REJECT_AREA_BELOW_MIN)

    def test_area_acima_ratio_rejeitada(self):
        walls = _retangulo_perfeito(10, 10, 520, 520)
        params = ParametrosDeteccaoRegioes(max_region_area_ratio=0.25)
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(len(resultado["regions"]), 0)
        self.assertEqual(resultado["rejected_regions"][0]["rejection_reason"], REJECT_AREA_ABOVE_PAGE_RATIO)

    def test_bbox_chave_dedup_aproximado(self):
        bbox1 = _bbox_celula(100, 200, 250, 350)
        bbox2 = _bbox_celula(101, 200, 249, 350)
        self.assertEqual(_bbox_chave(bbox1, 3.0), _bbox_chave(bbox2, 3.0))

    def test_edges_preservam_source_indices_e_count(self):
        resultado = detectar_regioes_pagina(_pagina_classificada(_retangulo_perfeito()))
        top = resultado["regions"][0]["edges"]["top"]
        self.assertIn(0, top["source_indices"])
        self.assertEqual(top["source_count"], len(top["source_indices"]))

    def test_stats_batem_com_pipeline(self):
        walls = _retangulo_perfeito()
        resultado = detectar_regioes_pagina(_pagina_classificada(walls))
        stats = resultado["stats"]
        self.assertEqual(stats["input_wall_candidates"], 4)
        self.assertEqual(stats["normalized_horizontal"], 2)
        self.assertEqual(stats["normalized_vertical"], 2)
        self.assertGreater(stats["grid_cells_checked"], 0)
        self.assertEqual(stats["candidate_regions"], len(resultado["regions"]))

    def test_sem_wall_candidates_retorna_zero(self):
        resultado = detectar_regioes_pagina(_pagina_classificada([]))
        self.assertEqual(resultado["regions"], [])
        self.assertEqual(resultado["stats"]["input_wall_candidates"], 0)

    def test_max_regions_truncated(self):
        walls = _retangulo_perfeito()
        walls.extend(_retangulo_perfeito(300, 200, 450, 350))
        params = ParametrosDeteccaoRegioes(max_regions=1)
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(len(resultado["regions"]), 1)
        self.assertTrue(resultado["truncated"])
        self.assertEqual(resultado["truncation_reason"], TRUNCATION_MAX_REGIONS)

    def test_max_rejected_regions_limita_amostra(self):
        params = ParametrosDeteccaoRegioes(
            min_region_area=10_000,
            max_rejected_regions=1,
        )
        walls = [
            *_retangulo_perfeito(10, 10, 30, 30),
            *_retangulo_perfeito(50, 50, 70, 70),
        ]
        resultado = detectar_regioes_pagina(_pagina_classificada(walls), params)
        self.assertEqual(resultado["stats"]["rejected_regions"], 2)
        self.assertEqual(resultado["stats"]["rejected_regions_saved"], 1)
        self.assertEqual(len(resultado["rejected_regions"]), 1)

    def test_salvar_regioes_grava_json(self):
        classificacao = {
            "source": "/tmp/x.pdf",
            "file_name": "x.pdf",
            "pages": [_pagina_classificada(_retangulo_perfeito())],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            destino = Path(tmpdir) / "x.regioes.json"
            salvar_regioes(classificacao, destino)
            payload = json.loads(destino.read_text(encoding="utf-8"))
        self.assertIn("region_detection_params", payload)
        self.assertIn("regions", payload["pages"][0])

    def test_integracao_real_classificada(self):
        json_path = Path(
            "data/output/saida/geometria_classificada/"
            "AY0410-ARQ-PL-0007-PLA-TIPO_TORRE01-R02.classificada.json"
        )
        if not json_path.exists():
            self.skipTest("JSON classificado real indisponivel")

        classificacao = json.loads(json_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmpdir:
            destino = Path(tmpdir) / "test.regioes.json"
            resultado = salvar_regioes(classificacao, destino)

        stats = resultado["pages"][0]["stats"]
        self.assertGreater(stats["input_wall_candidates"], 0)
        self.assertGreater(stats["merged_horizontal"], 0)
        self.assertGreater(stats["merged_vertical"], 0)
        self.assertGreater(stats["grid_cells_checked"], 0)
        self.assertIn("regions", resultado["pages"][0])


if __name__ == "__main__":
    unittest.main()
