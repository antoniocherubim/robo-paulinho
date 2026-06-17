"""Classificacao diagnostica de elementos vetoriais de inventarios PDF.

Separa candidatos a parede/contorno de ruidos graficos de forma conservadora.
Nao detecta ambientes nem calcula areas.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Razoes de classificacao (exclusive buckets de linhas)
REASON_LENGTH_NEAR_ZERO = "length_near_zero"
REASON_ORIENTATION_POINT = "orientation_point"
REASON_LENGTH_BELOW_MIN = "length_below_min_length_wall"
REASON_ORIENTATION_DIAGONAL = "orientation_diagonal"
REASON_TITLEBLOCK_STRONG = "inside_titleblock_region_strong"
REASON_TITLEBLOCK_SUSPECT = "inside_titleblock_region_suspect"
REASON_NEAR_TEXT_DENSITY = "near_text_density"
REASON_AXIS_ALIGNED_LONG = "axis_aligned_long_segment"

BUCKETS_EXCLUSIVOS_LINHAS = (
    "wall_candidates",
    "diagonal_segments",
    "thin_noise",
    "short_noise",
    "text_nearby_noise",
    "titleblock_or_legend_noise",
)


@dataclass(frozen=True)
class ParametrosClassificacao:
    """Parametros conservadores para classificacao vetorial."""

    min_length_wall: float = 10.0
    min_length_point: float = 0.5
    titleblock_right_ratio: float = 0.72
    titleblock_bottom_ratio: float = 0.72
    text_near_radius: float = 12.0
    text_near_min_count: int = 4
    rect_near_min_count: int = 3


def _comprimento(linha: dict[str, Any]) -> float:
    valor = linha.get("length")
    if valor is not None:
        return float(valor)
    x0 = float(linha.get("x0") or 0)
    x1 = float(linha.get("x1") or 0)
    top = float(linha.get("top") or 0)
    bottom = float(linha.get("bottom") if linha.get("bottom") is not None else top)
    return math.hypot(x1 - x0, bottom - top)


def _centroide(linha: dict[str, Any]) -> tuple[float, float]:
    if linha.get("cx") is not None and linha.get("cy") is not None:
        return float(linha["cx"]), float(linha["cy"])
    x0 = float(linha.get("x0") or 0)
    x1 = float(linha.get("x1") or 0)
    top = float(linha.get("top") or 0)
    bottom = float(linha.get("bottom") if linha.get("bottom") is not None else top)
    return (x0 + x1) / 2, (top + bottom) / 2


def _preservar_linha(linha: dict[str, Any], classification_reason: str) -> dict[str, Any]:
    campos = (
        "x0",
        "top",
        "x1",
        "bottom",
        "length",
        "linewidth",
        "orientation",
        "cx",
        "cy",
        "stroke",
        "fill",
    )
    item = {k: linha.get(k) for k in campos if k in linha}
    if item.get("length") is None:
        item["length"] = round(_comprimento(linha), 3)
    item["classification_reason"] = classification_reason
    return item


def _distancia_ponto_segmento(
    px: float,
    py: float,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> float:
    dx = x1 - x0
    dy = y1 - y0
    if dx == 0 and dy == 0:
        return math.hypot(px - x0, py - y0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy)))
    proj_x = x0 + t * dx
    proj_y = y0 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _regiao_carimbo(
    cx: float,
    cy: float,
    width: float,
    height: float,
    params: ParametrosClassificacao,
) -> tuple[bool, bool]:
    """Retorna (carimbo_forte, carimbo_suspeito)."""
    limite_direita = width * params.titleblock_right_ratio
    limite_inferior = height * params.titleblock_bottom_ratio
    direita = cx > limite_direita
    inferior = cy > limite_inferior
    forte = direita and inferior
    suspeito = (direita or inferior) and not forte
    return forte, suspeito


def contar_textos_proximos(
    linha: dict[str, Any],
    textos: list[dict[str, Any]],
    radius: float,
) -> int:
    x0 = float(linha.get("x0") or 0)
    x1 = float(linha.get("x1") or 0)
    top = float(linha.get("top") or 0)
    bottom = float(linha.get("bottom") if linha.get("bottom") is not None else top)
    total = 0
    for texto in textos:
        tcx = texto.get("cx")
        tcy = texto.get("cy")
        if tcx is None or tcy is None:
            tcx = float(texto.get("x0") or 0)
            tcy = float(texto.get("top") or 0)
        if _distancia_ponto_segmento(float(tcx), float(tcy), x0, top, x1, bottom) <= radius:
            total += 1
    return total


def contar_retangulos_proximos(
    linha: dict[str, Any],
    retangulos: list[dict[str, Any]],
    radius: float,
) -> int:
    x0 = float(linha.get("x0") or 0)
    x1 = float(linha.get("x1") or 0)
    top = float(linha.get("top") or 0)
    bottom = float(linha.get("bottom") if linha.get("bottom") is not None else top)
    total = 0
    for rect in retangulos:
        rcx = rect.get("cx")
        rcy = rect.get("cy")
        if rcx is None or rcy is None:
            rcx = float(rect.get("x0") or 0)
            rcy = float(rect.get("top") or 0)
        if _distancia_ponto_segmento(float(rcx), float(rcy), x0, top, x1, bottom) <= radius:
            total += 1
    return total


def _forma_em_carimbo_forte(
    forma: dict[str, Any],
    width: float,
    height: float,
    params: ParametrosClassificacao,
) -> bool:
    cx, cy = _centroide(forma)
    forte, _ = _regiao_carimbo(cx, cy, width, height, params)
    return forte


def _classificar_linha_exclusiva(
    linha: dict[str, Any],
    pagina: dict[str, Any],
    params: ParametrosClassificacao,
) -> tuple[str, dict[str, Any]]:
    width = float(pagina.get("width") or 1)
    height = float(pagina.get("height") or 1)
    textos = pagina.get("texts") or []
    retangulos = pagina.get("rects") or []

    orientacao = linha.get("orientation") or ""
    comprimento = _comprimento(linha)
    cx, cy = _centroide(linha)
    carimbo_forte, carimbo_suspeito = _regiao_carimbo(cx, cy, width, height, params)

    if orientacao == "ponto":
        return "thin_noise", _preservar_linha(linha, REASON_ORIENTATION_POINT)
    if comprimento < params.min_length_point:
        return "thin_noise", _preservar_linha(linha, REASON_LENGTH_NEAR_ZERO)
    if comprimento < params.min_length_wall:
        return "short_noise", _preservar_linha(linha, REASON_LENGTH_BELOW_MIN)
    if orientacao == "diagonal":
        return "diagonal_segments", _preservar_linha(linha, REASON_ORIENTATION_DIAGONAL)

    textos_proximos = contar_textos_proximos(linha, textos, params.text_near_radius)
    rects_proximos = contar_retangulos_proximos(linha, retangulos, params.text_near_radius)

    if carimbo_forte:
        return (
            "titleblock_or_legend_noise",
            _preservar_linha(linha, REASON_TITLEBLOCK_STRONG),
        )

    if carimbo_suspeito and (
        textos_proximos >= params.text_near_min_count
        or rects_proximos >= params.rect_near_min_count
    ):
        return (
            "titleblock_or_legend_noise",
            _preservar_linha(linha, REASON_TITLEBLOCK_SUSPECT),
        )

    if textos_proximos >= params.text_near_min_count:
        return (
            "text_nearby_noise",
            _preservar_linha(linha, REASON_NEAR_TEXT_DENSITY),
        )

    if orientacao in {"horizontal", "vertical"}:
        return (
            "wall_candidates",
            _preservar_linha(linha, REASON_AXIS_ALIGNED_LONG),
        )

    return "diagonal_segments", _preservar_linha(linha, REASON_ORIENTATION_DIAGONAL)


def _eixo_alinhado_longo(linha: dict[str, Any], params: ParametrosClassificacao) -> bool:
    orientacao = linha.get("orientation") or ""
    return orientacao in {"horizontal", "vertical"} and _comprimento(linha) >= params.min_length_wall


def classificar_pagina(
    pagina: dict[str, Any],
    params: ParametrosClassificacao | None = None,
) -> dict[str, Any]:
    """Classifica linhas, retangulos e curvas de uma pagina inventariada."""
    params = params or ParametrosClassificacao()
    width = float(pagina.get("width") or 1)
    height = float(pagina.get("height") or 1)

    classified: dict[str, list[dict[str, Any]]] = {
        "wall_candidates": [],
        "axis_aligned_segments": [],
        "diagonal_segments": [],
        "thin_noise": [],
        "short_noise": [],
        "text_nearby_noise": [],
        "titleblock_or_legend_noise": [],
        "rect_candidates": [],
        "curve_candidates": [],
    }

    linhas = pagina.get("lines") or []
    bucket_por_indice: dict[int, str] = {}

    for indice, linha in enumerate(linhas):
        bucket, item = _classificar_linha_exclusiva(linha, pagina, params)
        classified[bucket].append(item)
        bucket_por_indice[indice] = bucket

        if _eixo_alinhado_longo(linha, params):
            roll = dict(item)
            roll["exclusive_bucket"] = bucket
            classified["axis_aligned_segments"].append(roll)

    for rect in pagina.get("rects") or []:
        if _forma_em_carimbo_forte(rect, width, height, params):
            continue
        item = {k: rect.get(k) for k in ("x0", "top", "x1", "bottom", "width", "height", "cx", "cy", "linewidth") if k in rect}
        item["classification_reason"] = "rect_outside_titleblock"
        classified["rect_candidates"].append(item)

    for curva in pagina.get("curves") or []:
        if _forma_em_carimbo_forte(curva, width, height, params):
            continue
        item = {k: curva.get(k) for k in ("x0", "top", "x1", "bottom", "width", "height", "cx", "cy", "linewidth", "point_count") if k in curva}
        item["classification_reason"] = "curve_outside_titleblock"
        classified["curve_candidates"].append(item)

    exclusive_count = sum(len(classified[b]) for b in BUCKETS_EXCLUSIVOS_LINHAS)
    discarded = exclusive_count - len(classified["wall_candidates"])

    stats = {
        "input_lines": len(linhas),
        "exclusive_classified_lines": exclusive_count,
        "wall_candidates": len(classified["wall_candidates"]),
        "discarded_noise": discarded,
        "axis_aligned_segments": len(classified["axis_aligned_segments"]),
        "input_rects": len(pagina.get("rects") or []),
        "rect_candidates": len(classified["rect_candidates"]),
        "input_curves": len(pagina.get("curves") or []),
        "curve_candidates": len(classified["curve_candidates"]),
    }

    return {
        "page_number": pagina.get("page_number"),
        "width": pagina.get("width"),
        "height": pagina.get("height"),
        "coordinate_system": pagina.get("coordinate_system"),
        "classified": classified,
        "stats": stats,
    }


def classificar_inventario(
    inventario: dict[str, Any],
    params: ParametrosClassificacao | None = None,
) -> dict[str, Any]:
    """Classifica todas as paginas de um inventario geometrico."""
    params = params or ParametrosClassificacao()
    paginas = [classificar_pagina(p, params) for p in inventario.get("pages") or []]
    return {
        "source": inventario.get("source"),
        "file_name": inventario.get("file_name"),
        "page_count": len(paginas),
        "classification_params": asdict(params),
        "pages": paginas,
    }


def _stem_inventario(file_name: str | None, caminho_json: Path | None = None) -> str:
    if file_name:
        nome = Path(file_name).stem
        if nome.endswith(".geometria"):
            return nome[: -len(".geometria")]
        return nome
    if caminho_json is not None:
        stem = caminho_json.stem
        if stem.endswith(".geometria"):
            return stem[: -len(".geometria")]
        return stem
    return "inventario"


def salvar_classificacao(
    inventario: dict[str, Any],
    caminho_saida: str | Path,
    params: ParametrosClassificacao | None = None,
) -> dict[str, Any]:
    """Classifica inventario e grava JSON UTF-8 indentado."""
    resultado = classificar_inventario(inventario, params=params)
    saida = Path(caminho_saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultado
