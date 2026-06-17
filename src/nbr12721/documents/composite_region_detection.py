"""Deteccao de regioes compostas a partir de celulas fechadas adjacentes."""
from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from nbr12721.documents.region_detection import (
    REJECT_AREA_ABOVE_PAGE_RATIO,
    REJECT_AREA_BELOW_MIN,
    REJECT_HEIGHT_BELOW_MIN,
    REJECT_WIDTH_BELOW_MIN,
)

DETECTION_STRATEGY = "connected_cell_components_v1"
COMPOSITE_SOURCE = "connected_cell_components_from_closed_cells"

REJECT_FILL_RATIO_BELOW_MIN = "fill_ratio_below_min"
REJECT_SINGLE_CELL_COMPONENT = "single_cell_component"
REJECT_TOO_MANY_CELLS = "too_many_cells"
REJECT_WIDTH_ABOVE_PAGE_RATIO = "width_above_page_ratio"
REJECT_HEIGHT_ABOVE_PAGE_RATIO = "height_above_page_ratio"
TRUNCATION_MAX_COMPOSITES = "max_composites"

COMPOSITION_SINGLE_EXISTING = "single_existing_region"
COMPOSITION_CONNECTED = "connected_cells"


@dataclass(frozen=True)
class ParametrosRegioesCompostas:
    adjacency_tolerance: float = 3.0
    min_composite_width: float = 20.0
    min_composite_height: float = 20.0
    min_composite_area: float = 400.0
    min_fill_ratio: float = 0.05
    max_composite_area_ratio: float = 0.25
    max_composite_width_ratio: float = 0.50
    max_composite_height_ratio: float = 0.50
    max_cells_per_component: int = 200
    max_composites: int = 5000
    max_rejected_composites: int = 1000
    include_rejected_reasons: tuple[str, ...] = (
        REJECT_WIDTH_BELOW_MIN,
        REJECT_HEIGHT_BELOW_MIN,
        REJECT_AREA_BELOW_MIN,
    )


def _stem_regioes(file_name: str | None, caminho_json: Path | None = None) -> str:
    if caminho_json is not None:
        stem = caminho_json.stem
        if stem.endswith(".regioes"):
            return stem[: -len(".regioes")]
        return stem
    if file_name:
        nome = Path(file_name).stem
        if nome.endswith(".regioes"):
            return nome[: -len(".regioes")]
        return nome
    return "regioes"


def _overlap_1d(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> float:
    return max(0.0, min(hi_a, hi_b) - max(lo_a, lo_b))


def _normalizar_celula_base(regiao: dict[str, Any], *, was_accepted_region: bool) -> dict[str, Any] | None:
    bbox = regiao.get("bbox")
    if not bbox:
        return None
    required = ("x0", "top", "x1", "bottom", "width", "height", "area_pdf_units")
    if any(bbox.get(k) is None for k in required):
        return None
    return {
        "id": regiao.get("id"),
        "bbox": dict(bbox),
        "centroid": dict(regiao.get("centroid") or {}),
        "edges": regiao.get("edges"),
        "original_confidence": regiao.get("confidence", ""),
        "original_rejection_reason": regiao.get("rejection_reason") or "",
        "was_accepted_region": was_accepted_region,
    }


def coletar_celulas_base(
    page: dict[str, Any],
    params: ParametrosRegioesCompostas | None = None,
) -> list[dict[str, Any]]:
    """Coleta celulas fechadas elegiveis para composicao."""
    params = params or ParametrosRegioesCompostas()
    celulas: list[dict[str, Any]] = []

    for regiao in page.get("regions") or []:
        item = _normalizar_celula_base(regiao, was_accepted_region=True)
        if item:
            celulas.append(item)

    for regiao in page.get("rejected_regions") or []:
        motivo = regiao.get("rejection_reason") or ""
        if motivo == REJECT_AREA_ABOVE_PAGE_RATIO:
            continue
        if motivo and motivo not in params.include_rejected_reasons:
            continue
        item = _normalizar_celula_base(regiao, was_accepted_region=False)
        if item:
            celulas.append(item)

    return celulas


def celulas_sao_adjacentes(
    a: dict[str, Any],
    b: dict[str, Any],
    params: ParametrosRegioesCompostas | None = None,
) -> bool:
    """Verifica adjacencia ortogonal entre duas celulas."""
    params = params or ParametrosRegioesCompostas()
    tol = params.adjacency_tolerance
    ba = a["bbox"]
    bb = b["bbox"]

    overlap_vertical = _overlap_1d(ba["top"], ba["bottom"], bb["top"], bb["bottom"])
    overlap_horizontal = _overlap_1d(ba["x0"], ba["x1"], bb["x0"], bb["x1"])
    min_vert = min(float(ba["height"]), float(bb["height"])) * 0.25
    min_horiz = min(float(ba["width"]), float(bb["width"])) * 0.25

    horizontal_touch = (
        abs(float(ba["x1"]) - float(bb["x0"])) <= tol
        or abs(float(bb["x1"]) - float(ba["x0"])) <= tol
    )
    vertical_touch = (
        abs(float(ba["bottom"]) - float(bb["top"])) <= tol
        or abs(float(bb["bottom"]) - float(ba["top"])) <= tol
    )

    if horizontal_touch and overlap_vertical >= max(tol, min_vert):
        return True
    if vertical_touch and overlap_horizontal >= max(tol, min_horiz):
        return True
    return False


def detectar_componentes_celulas(
    cells: list[dict[str, Any]],
    params: ParametrosRegioesCompostas | None = None,
) -> tuple[list[list[dict[str, Any]]], list[list[int]], int, int]:
    """Retorna componentes conectados, grafo de adjacencia, arestas e pair_checks."""
    params = params or ParametrosRegioesCompostas()
    n = len(cells)
    if n == 0:
        return [], [], 0, 0

    adj: list[list[int]] = [[] for _ in range(n)]
    pair_checks = 0
    edge_count = 0

    for i in range(n):
        for j in range(i + 1, n):
            pair_checks += 1
            if celulas_sao_adjacentes(cells[i], cells[j], params):
                adj[i].append(j)
                adj[j].append(i)
                edge_count += 1

    visitados = [False] * n
    componentes: list[list[dict[str, Any]]] = []

    for i in range(n):
        if visitados[i]:
            continue
        fila: deque[int] = deque([i])
        visitados[i] = True
        grupo: list[dict[str, Any]] = []
        while fila:
            atual = fila.popleft()
            grupo.append(cells[atual])
            for vizinho in adj[atual]:
                if not visitados[vizinho]:
                    visitados[vizinho] = True
                    fila.append(vizinho)
        componentes.append(grupo)

    return componentes, adj, edge_count, pair_checks


def _bbox_uniao(celulas: list[dict[str, Any]]) -> dict[str, float]:
    x0 = min(float(c["bbox"]["x0"]) for c in celulas)
    top = min(float(c["bbox"]["top"]) for c in celulas)
    x1 = max(float(c["bbox"]["x1"]) for c in celulas)
    bottom = max(float(c["bbox"]["bottom"]) for c in celulas)
    width = x1 - x0
    height = bottom - top
    return {
        "x0": round(x0, 3),
        "top": round(top, 3),
        "x1": round(x1, 3),
        "bottom": round(bottom, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "area_pdf_units": round(width * height, 3),
    }


def _bbox_chave(bbox: dict[str, float], tol: float) -> tuple[int, int, int, int]:
    if tol <= 0:
        tol = 1.0
    return (
        int(bbox["x0"] / tol),
        int(bbox["top"] / tol),
        int(bbox["x1"] / tol),
        int(bbox["bottom"] / tol),
    )


def _adjacency_edge_count_componente(indices: set[int], adj: list[list[int]]) -> int:
    count = 0
    for i in indices:
        for j in adj[i]:
            if j > i and j in indices:
                count += 1
    return count


def _agregar_componente(
    celulas: list[dict[str, Any]],
    indices: set[int],
    adj: list[list[int]],
) -> dict[str, Any]:
    bbox = _bbox_uniao(celulas)
    cell_area_sum = round(sum(float(c["bbox"]["area_pdf_units"]) for c in celulas), 3)
    bbox_area = float(bbox["area_pdf_units"]) or 1.0
    fill_ratio = round(cell_area_sum / bbox_area, 4) if bbox_area else 0.0

    source_confidences = sorted({c["original_confidence"] for c in celulas if c.get("original_confidence")})
    source_rejection_reasons = sorted(
        {c["original_rejection_reason"] for c in celulas if c.get("original_rejection_reason")}
    )

    cell_count = len(celulas)
    if cell_count >= 2:
        composition_type = COMPOSITION_CONNECTED
    elif any(c.get("was_accepted_region") for c in celulas):
        composition_type = COMPOSITION_SINGLE_EXISTING
    else:
        composition_type = COMPOSITION_CONNECTED

    return {
        "bbox": bbox,
        "centroid": {
            "x": round((bbox["x0"] + bbox["x1"]) / 2, 3),
            "y": round((bbox["top"] + bbox["bottom"]) / 2, 3),
        },
        "cell_count": cell_count,
        "source_cell_ids": [c["id"] for c in celulas],
        "source_confidences": source_confidences,
        "source_rejection_reasons": source_rejection_reasons,
        "cell_area_sum_pdf_units": cell_area_sum,
        "fill_ratio": fill_ratio,
        "width_ratio": None,
        "height_ratio": None,
        "adjacency_edge_count": _adjacency_edge_count_componente(indices, adj),
        "composition_type": composition_type,
        "source": COMPOSITE_SOURCE,
    }


def _avaliar_componente(
    comp: dict[str, Any],
    page_width: float,
    page_height: float,
    params: ParametrosRegioesCompostas,
) -> str | None:
    bbox = comp["bbox"]
    page_area = page_width * page_height

    if comp["cell_count"] < 2 and comp["composition_type"] != COMPOSITION_SINGLE_EXISTING:
        return REJECT_SINGLE_CELL_COMPONENT
    if comp["cell_count"] > params.max_cells_per_component:
        return REJECT_TOO_MANY_CELLS
    if bbox["width"] < params.min_composite_width:
        return REJECT_WIDTH_BELOW_MIN
    if bbox["height"] < params.min_composite_height:
        return REJECT_HEIGHT_BELOW_MIN
    if bbox["area_pdf_units"] < params.min_composite_area:
        return REJECT_AREA_BELOW_MIN
    if comp["fill_ratio"] < params.min_fill_ratio:
        return REJECT_FILL_RATIO_BELOW_MIN

    if page_area > 0 and bbox["area_pdf_units"] > page_area * params.max_composite_area_ratio:
        return REJECT_AREA_ABOVE_PAGE_RATIO
    if page_width > 0:
        comp["width_ratio"] = round(float(bbox["width"]) / page_width, 4)
        if comp["width_ratio"] > params.max_composite_width_ratio:
            return REJECT_WIDTH_ABOVE_PAGE_RATIO
    if page_height > 0:
        comp["height_ratio"] = round(float(bbox["height"]) / page_height, 4)
        if comp["height_ratio"] > params.max_composite_height_ratio:
            return REJECT_HEIGHT_ABOVE_PAGE_RATIO

    return None


def detectar_regioes_compostas_pagina(
    page: dict[str, Any],
    params: ParametrosRegioesCompostas | None = None,
) -> dict[str, Any]:
    """Detecta regioes compostas em uma pagina de regioes detectadas."""
    params = params or ParametrosRegioesCompostas()
    page_number = int(page.get("page_number") or 1)
    page_width = float(page.get("width") or 1)
    page_height = float(page.get("height") or 1)

    input_regions = len(page.get("regions") or [])
    input_rejected = len(page.get("rejected_regions") or [])

    celulas = coletar_celulas_base(page, params)
    componentes, adj, adjacency_edges, pair_checks = detectar_componentes_celulas(celulas, params)

    indice_por_id = {c["id"]: i for i, c in enumerate(celulas)}

    composite_regions: list[dict[str, Any]] = []
    rejected_all: list[dict[str, Any]] = []
    rejected_saved: list[dict[str, Any]] = []
    vistos: set[tuple[int, int, int, int]] = set()
    duplicate_composites = 0
    truncated = False
    truncation_reason = ""
    comp_seq = 0
    rej_seq = 0

    for grupo in componentes:
        if truncated:
            break
        indices = {indice_por_id[c["id"]] for c in grupo if c["id"] in indice_por_id}
        agregado = _agregar_componente(grupo, indices, adj)

        chave = _bbox_chave(agregado["bbox"], params.adjacency_tolerance)
        if chave in vistos:
            duplicate_composites += 1
            continue
        vistos.add(chave)

        motivo = _avaliar_componente(agregado, page_width, page_height, params)
        if motivo:
            rej_seq += 1
            rejeitada = {
                "id": f"p{page_number:03d}_x{rej_seq:04d}",
                **agregado,
                "confidence": "rejected",
                "rejection_reason": motivo,
            }
            rejected_all.append(rejeitada)
            if len(rejected_saved) < params.max_rejected_composites:
                rejected_saved.append(rejeitada)
            continue

        if len(composite_regions) >= params.max_composites:
            truncated = True
            truncation_reason = TRUNCATION_MAX_COMPOSITES
            break

        comp_seq += 1
        composite_regions.append(
            {
                "id": f"p{page_number:03d}_c{comp_seq:04d}",
                **agregado,
                "confidence": "candidate",
                "rejection_reason": "",
            }
        )

    stats = {
        "input_regions": input_regions,
        "input_rejected_regions": input_rejected,
        "base_cells": len(celulas),
        "pair_checks": pair_checks,
        "adjacency_edges": adjacency_edges,
        "components_found": len(componentes),
        "candidate_composites": len(composite_regions),
        "rejected_composites": len(rejected_all),
        "rejected_composites_saved": len(rejected_saved),
        "duplicate_composites": duplicate_composites,
    }

    return {
        "page_number": page_number,
        "width": page.get("width"),
        "height": page.get("height"),
        "coordinate_system": page.get("coordinate_system"),
        "detection_strategy": DETECTION_STRATEGY,
        "composite_regions": composite_regions,
        "rejected_composite_regions": rejected_saved,
        "truncated": truncated,
        "truncation_reason": truncation_reason,
        "stats": stats,
    }


def detectar_regioes_compostas_documento(
    regioes_doc: dict[str, Any],
    params: ParametrosRegioesCompostas | None = None,
) -> dict[str, Any]:
    """Detecta regioes compostas em todas as paginas."""
    params = params or ParametrosRegioesCompostas()
    paginas = [detectar_regioes_compostas_pagina(p, params) for p in regioes_doc.get("pages") or []]
    return {
        "source": regioes_doc.get("source"),
        "file_name": regioes_doc.get("file_name"),
        "page_count": len(paginas),
        "composite_region_params": asdict(params),
        "pages": paginas,
    }


def salvar_regioes_compostas(
    regioes_doc: dict[str, Any],
    caminho_saida: str | Path,
    params: ParametrosRegioesCompostas | None = None,
) -> dict[str, Any]:
    """Detecta regioes compostas e grava JSON UTF-8 indentado."""
    resultado = detectar_regioes_compostas_documento(regioes_doc, params=params)
    saida = Path(caminho_saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado
