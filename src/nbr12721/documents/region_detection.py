"""Deteccao diagnostica de celulas/regioes ortogonais a partir de wall_candidates."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DETECTION_STRATEGY_V1 = "adjacent_grid_v1"
REGION_SOURCE = "orthogonal_cell_from_wall_candidates"

REJECT_WIDTH_BELOW_MIN = "width_below_min"
REJECT_HEIGHT_BELOW_MIN = "height_below_min"
REJECT_AREA_BELOW_MIN = "area_below_min"
REJECT_AREA_ABOVE_PAGE_RATIO = "area_above_page_ratio"
TRUNCATION_MAX_REGIONS = "max_regions"


@dataclass(frozen=True)
class ParametrosDeteccaoRegioes:
    merge_tolerance: float = 2.0
    snap_tolerance: float = 3.0
    min_region_width: float = 8.0
    min_region_height: float = 8.0
    min_region_area: float = 100.0
    max_region_area_ratio: float = 0.25
    max_regions: int = 5000
    max_rejected_regions: int = 1000


def _stem_classificacao(file_name: str | None, caminho_json: Path | None = None) -> str:
    if caminho_json is not None:
        stem = caminho_json.stem
        if stem.endswith(".classificada"):
            return stem[: -len(".classificada")]
        return stem
    if file_name:
        nome = Path(file_name).stem
        if nome.endswith(".classificada"):
            return nome[: -len(".classificada")]
        return nome
    return "classificacao"


def _normalizar_linha(linha: dict[str, Any], source_index: int) -> dict[str, Any] | None:
    orientacao = linha.get("orientation") or ""
    x0 = float(linha.get("x0") or 0)
    x1 = float(linha.get("x1") or 0)
    top = float(linha.get("top") or 0)
    bottom = float(linha.get("bottom") if linha.get("bottom") is not None else top)

    if orientacao == "horizontal":
        pos = top
        start = min(x0, x1)
        end = max(x0, x1)
    elif orientacao == "vertical":
        pos = x0
        start = min(top, bottom)
        end = max(top, bottom)
    else:
        return None

    return {
        "orientation": orientacao,
        "pos": round(pos, 3),
        "start": round(start, 3),
        "end": round(end, 3),
        "source_index": source_index,
        "source_indices": [source_index],
        "length": linha.get("length"),
    }


def normalizar_segmentos(
    classified_page: dict[str, Any],
    params: ParametrosDeteccaoRegioes | None = None,
) -> dict[str, Any]:
    """Normaliza wall_candidates em segmentos horizontais e verticais."""
    _ = params
    horizontais: list[dict[str, Any]] = []
    verticais: list[dict[str, Any]] = []

    for indice, linha in enumerate(classified_page.get("classified", {}).get("wall_candidates") or []):
        item = _normalizar_linha(linha, indice)
        if item is None:
            continue
        if item["orientation"] == "horizontal":
            horizontais.append(item)
        else:
            verticais.append(item)

    return {
        "horizontal": horizontais,
        "vertical": verticais,
    }


def _mesclar_grupo(segmentos: list[dict[str, Any]], merge_tolerance: float) -> list[dict[str, Any]]:
    if not segmentos:
        return []
    ordenados = sorted(segmentos, key=lambda s: (s["start"], s["end"]))
    mesclados: list[dict[str, Any]] = []
    atual = dict(ordenados[0])
    atual["source_indices"] = list(atual["source_indices"])

    for seg in ordenados[1:]:
        if seg["start"] <= atual["end"] + merge_tolerance:
            atual["end"] = max(atual["end"], seg["end"])
            for idx in seg["source_indices"]:
                if idx not in atual["source_indices"]:
                    atual["source_indices"].append(idx)
        else:
            mesclados.append(atual)
            atual = dict(seg)
            atual["source_indices"] = list(atual["source_indices"])

    mesclados.append(atual)
    return mesclados


def _mesclar_por_orientacao(
    segmentos: list[dict[str, Any]],
    merge_tolerance: float,
) -> list[dict[str, Any]]:
    if not segmentos:
        return []

    ordenados = sorted(segmentos, key=lambda s: s["pos"])
    grupos: list[list[dict[str, Any]]] = []
    grupo_atual = [ordenados[0]]

    for seg in ordenados[1:]:
        if abs(seg["pos"] - grupo_atual[-1]["pos"]) <= merge_tolerance:
            grupo_atual.append(seg)
        else:
            grupos.append(grupo_atual)
            grupo_atual = [seg]
    grupos.append(grupo_atual)

    mesclados: list[dict[str, Any]] = []
    for grupo in grupos:
        pos_media = round(sum(s["pos"] for s in grupo) / len(grupo), 3)
        for item in _mesclar_grupo(grupo, merge_tolerance):
            item["pos"] = pos_media
            mesclados.append(item)
    return mesclados


def _cobre_horizontal(
    segmentos: list[dict[str, Any]],
    y: float,
    x_start: float,
    x_end: float,
    snap: float,
) -> dict[str, Any] | None:
    for seg in segmentos:
        if abs(seg["pos"] - y) <= snap and seg["start"] <= x_start + snap and seg["end"] >= x_end - snap:
            return seg
    return None


def _cobre_vertical(
    segmentos: list[dict[str, Any]],
    x: float,
    y_start: float,
    y_end: float,
    snap: float,
) -> dict[str, Any] | None:
    for seg in segmentos:
        if abs(seg["pos"] - x) <= snap and seg["start"] <= y_start + snap and seg["end"] >= y_end - snap:
            return seg
    return None


def _edge_from_segmento(seg: dict[str, Any]) -> dict[str, Any]:
    indices = list(seg["source_indices"])
    return {
        "pos": seg["pos"],
        "start": seg["start"],
        "end": seg["end"],
        "source_indices": indices,
        "source_count": len(indices),
    }


def _bbox_celula(left: float, top: float, right: float, bottom: float) -> dict[str, float]:
    width = right - left
    height = bottom - top
    return {
        "x0": round(left, 3),
        "top": round(top, 3),
        "x1": round(right, 3),
        "bottom": round(bottom, 3),
        "width": round(width, 3),
        "height": round(height, 3),
        "area_pdf_units": round(width * height, 3),
    }


def _bbox_chave(bbox: dict[str, float], snap: float) -> tuple[int, int, int, int]:
    if snap <= 0:
        snap = 1.0
    return (
        int(bbox["x0"] / snap),
        int(bbox["top"] / snap),
        int(bbox["x1"] / snap),
        int(bbox["bottom"] / snap),
    )


def _montar_regiao(
    region_id: str,
    bbox: dict[str, float],
    edges: dict[str, Any],
    *,
    confidence: str,
    rejection_reason: str,
) -> dict[str, Any]:
    return {
        "id": region_id,
        "bbox": bbox,
        "centroid": {
            "x": round((bbox["x0"] + bbox["x1"]) / 2, 3),
            "y": round((bbox["top"] + bbox["bottom"]) / 2, 3),
        },
        "edges": edges,
        "source": REGION_SOURCE,
        "confidence": confidence,
        "rejection_reason": rejection_reason,
    }


def _avaliar_filtros(
    bbox: dict[str, float],
    page_width: float,
    page_height: float,
    params: ParametrosDeteccaoRegioes,
) -> str | None:
    if bbox["width"] < params.min_region_width:
        return REJECT_WIDTH_BELOW_MIN
    if bbox["height"] < params.min_region_height:
        return REJECT_HEIGHT_BELOW_MIN
    if bbox["area_pdf_units"] < params.min_region_area:
        return REJECT_AREA_BELOW_MIN
    page_area = page_width * page_height
    if page_area > 0 and bbox["area_pdf_units"] > page_area * params.max_region_area_ratio:
        return REJECT_AREA_ABOVE_PAGE_RATIO
    return None


def detectar_regioes_pagina(
    classified_page: dict[str, Any],
    params: ParametrosDeteccaoRegioes | None = None,
) -> dict[str, Any]:
    """Detecta celulas ortogonais fechadas em uma pagina classificada."""
    params = params or ParametrosDeteccaoRegioes()
    page_number = int(classified_page.get("page_number") or 1)
    page_width = float(classified_page.get("width") or 1)
    page_height = float(classified_page.get("height") or 1)
    wall_candidates = classified_page.get("classified", {}).get("wall_candidates") or []

    normalizado = normalizar_segmentos(classified_page, params)
    horizontais = _mesclar_por_orientacao(normalizado["horizontal"], params.merge_tolerance)
    verticais = _mesclar_por_orientacao(normalizado["vertical"], params.merge_tolerance)

    ys = sorted({seg["pos"] for seg in horizontais})
    xs = sorted({seg["pos"] for seg in verticais})

    regions: list[dict[str, Any]] = []
    rejected_all: list[dict[str, Any]] = []
    rejected_saved: list[dict[str, Any]] = []
    vistos: set[tuple[float, float, float, float]] = set()
    duplicate_regions = 0
    grid_cells_checked = 0
    closed_cells_found = 0
    truncated = False
    truncation_reason = ""
    region_seq = 0
    rejected_seq = 0

    for i in range(len(ys) - 1):
        if truncated:
            break
        top_y = ys[i]
        bottom_y = ys[i + 1]
        for j in range(len(xs) - 1):
            if truncated:
                break
            left_x = xs[j]
            right_x = xs[j + 1]
            grid_cells_checked += 1

            seg_top = _cobre_horizontal(horizontais, top_y, left_x, right_x, params.snap_tolerance)
            seg_bottom = _cobre_horizontal(horizontais, bottom_y, left_x, right_x, params.snap_tolerance)
            seg_left = _cobre_vertical(verticais, left_x, top_y, bottom_y, params.snap_tolerance)
            seg_right = _cobre_vertical(verticais, right_x, top_y, bottom_y, params.snap_tolerance)

            if not (seg_top and seg_bottom and seg_left and seg_right):
                continue

            closed_cells_found += 1
            bbox = _bbox_celula(left_x, top_y, right_x, bottom_y)
            edges = {
                "top": _edge_from_segmento(seg_top),
                "right": _edge_from_segmento(seg_right),
                "bottom": _edge_from_segmento(seg_bottom),
                "left": _edge_from_segmento(seg_left),
            }

            chave = _bbox_chave(bbox, params.snap_tolerance)
            if chave in vistos:
                duplicate_regions += 1
                continue
            vistos.add(chave)

            motivo = _avaliar_filtros(bbox, page_width, page_height, params)
            if motivo:
                rejected_seq += 1
                rejeitada = _montar_regiao(
                    f"p{page_number:03d}_x{rejected_seq:04d}",
                    bbox,
                    edges,
                    confidence="rejected",
                    rejection_reason=motivo,
                )
                rejected_all.append(rejeitada)
                if len(rejected_saved) < params.max_rejected_regions:
                    rejected_saved.append(rejeitada)
                continue

            if len(regions) >= params.max_regions:
                truncated = True
                truncation_reason = TRUNCATION_MAX_REGIONS
                break

            region_seq += 1
            regions.append(
                _montar_regiao(
                    f"p{page_number:03d}_r{region_seq:04d}",
                    bbox,
                    edges,
                    confidence="candidate",
                    rejection_reason="",
                )
            )

    stats = {
        "input_wall_candidates": len(wall_candidates),
        "normalized_horizontal": len(normalizado["horizontal"]),
        "normalized_vertical": len(normalizado["vertical"]),
        "merged_horizontal": len(horizontais),
        "merged_vertical": len(verticais),
        "grid_cells_checked": grid_cells_checked,
        "closed_cells_found": closed_cells_found,
        "candidate_regions": len(regions),
        "rejected_regions": len(rejected_all),
        "rejected_regions_saved": len(rejected_saved),
        "duplicate_regions": duplicate_regions,
    }

    return {
        "page_number": page_number,
        "width": classified_page.get("width"),
        "height": classified_page.get("height"),
        "coordinate_system": classified_page.get("coordinate_system"),
        "detection_strategy": DETECTION_STRATEGY_V1,
        "regions": regions,
        "rejected_regions": rejected_saved,
        "truncated": truncated,
        "truncation_reason": truncation_reason,
        "stats": stats,
    }


def detectar_regioes_classificacao(
    classificacao: dict[str, Any],
    params: ParametrosDeteccaoRegioes | None = None,
) -> dict[str, Any]:
    """Detecta regioes em todas as paginas de um inventario classificado."""
    params = params or ParametrosDeteccaoRegioes()
    paginas = [detectar_regioes_pagina(p, params) for p in classificacao.get("pages") or []]
    return {
        "source": classificacao.get("source"),
        "file_name": classificacao.get("file_name"),
        "page_count": len(paginas),
        "region_detection_params": asdict(params),
        "pages": paginas,
    }


def salvar_regioes(
    classificacao: dict[str, Any],
    caminho_saida: str | Path,
    params: ParametrosDeteccaoRegioes | None = None,
) -> dict[str, Any]:
    """Detecta regioes e grava JSON UTF-8 indentado."""
    resultado = detectar_regioes_classificacao(classificacao, params=params)
    saida = Path(caminho_saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado
