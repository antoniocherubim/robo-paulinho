"""Geracao de SVG diagnostico a partir de inventarios classificados vetorialmente."""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_MAX_WALL_CANDIDATES = 50_000
DEFAULT_MAX_NOISE = 50_000
DEFAULT_MAX_RECTS = 20_000
DEFAULT_MAX_CURVES = 20_000

_STYLES = """
  .geo-page { fill: #ffffff; }
  .cls-wall { stroke: #00cccc; stroke-width: 0.8; fill: none; opacity: 1; }
  .cls-axis { stroke: #88ddff; stroke-width: 0.35; fill: none; opacity: 0.25; }
  .cls-diagonal { stroke: #cc6600; stroke-width: 0.4; fill: none; }
  .cls-titleblock { stroke: #999999; stroke-width: 0.4; fill: none; }
  .cls-text-near { stroke: #ddaa00; stroke-width: 0.4; fill: none; opacity: 0.6; }
  .cls-short { stroke: #ff9999; stroke-width: 0.4; fill: none; }
  .cls-thin { stroke: #ffcccc; stroke-width: 0.2; fill: none; opacity: 0.5; }
  .cls-rect { stroke: #6633cc; stroke-width: 0.5; fill: none; }
  .cls-curve { stroke: #cc2222; stroke-width: 0.5; fill: none; stroke-dasharray: 2 2; }
  .geo-legend-text { fill: #111111; font-family: sans-serif; font-size: 6px; }
  .geo-legend-sample { stroke-width: 1.2; fill: none; }
""".strip()

_BUCKET_LAYER = {
    "wall_candidates": ("layer-wall-candidates", "cls-wall"),
    "axis_aligned_segments": ("layer-axis-aligned", "cls-axis"),
    "diagonal_segments": ("layer-diagonal", "cls-diagonal"),
    "titleblock_or_legend_noise": ("layer-titleblock-noise", "cls-titleblock"),
    "text_nearby_noise": ("layer-text-nearby-noise", "cls-text-near"),
    "short_noise": ("layer-short-noise", "cls-short"),
    "thin_noise": ("layer-thin-noise", "cls-thin"),
}

_NOISE_BUCKETS = (
    "diagonal_segments",
    "titleblock_or_legend_noise",
    "text_nearby_noise",
    "short_noise",
    "thin_noise",
)


@dataclass(frozen=True)
class LimitesClassificacaoSvg:
    max_wall_candidates: int = DEFAULT_MAX_WALL_CANDIDATES
    max_noise: int = DEFAULT_MAX_NOISE
    max_rects: int = DEFAULT_MAX_RECTS
    max_curves: int = DEFAULT_MAX_CURVES


def _escape_xml(texto: str) -> str:
    return escape(str(texto), quote=False)


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


def _nome_arquivo_svg(stem: str, page_number: int) -> str:
    return f"{stem}.p{page_number:03d}.classificada.debug.svg"


def _title_linha(item: dict[str, Any], bucket: str) -> str:
    partes = [
        f"bucket={bucket}",
        f"reason={item.get('classification_reason', '')}",
        f"orientation={item.get('orientation', '')}",
        f"length={item.get('length', '')}",
        (
            f"coords=({item.get('x0')},{item.get('top')})"
            f"-({item.get('x1')},{item.get('bottom')})"
        ),
    ]
    if bucket == "axis_aligned_segments" and item.get("exclusive_bucket"):
        partes.append(f"exclusive_bucket={item.get('exclusive_bucket')}")
    return _escape_xml(" | ".join(str(p) for p in partes))


def _title_forma(item: dict[str, Any], bucket: str) -> str:
    partes = [
        f"bucket={bucket}",
        f"reason={item.get('classification_reason', '')}",
        (
            f"bbox=({item.get('x0')},{item.get('top')})"
            f"+{item.get('width')}x{item.get('height')}"
        ),
    ]
    return _escape_xml(" | ".join(str(p) for p in partes))


def _render_linha(item: dict[str, Any], classe: str, bucket: str) -> str | None:
    x0 = item.get("x0")
    top = item.get("top")
    x1 = item.get("x1")
    bottom = item.get("bottom")
    if x0 is None or top is None or x1 is None or bottom is None:
        return None
    titulo = _title_linha(item, bucket)
    return (
        f'    <line class="{classe}" x1="{x0}" y1="{top}" x2="{x1}" y2="{bottom}">'
        f"<title>{titulo}</title></line>"
    )


def _layer_linhas(
    layer_id: str,
    classe: str,
    bucket: str,
    itens: list[dict[str, Any]],
) -> str:
    partes = [f'  <g id="{layer_id}">']
    for item in itens:
        linha = _render_linha(item, classe, bucket)
        if linha:
            partes.append(linha)
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_retangulos(itens: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-rect-candidates">']
    for item in itens:
        x0 = item.get("x0")
        top = item.get("top")
        width = item.get("width")
        height = item.get("height")
        if x0 is None or top is None or width is None or height is None:
            continue
        titulo = _title_forma(item, "rect_candidates")
        partes.append(
            f'    <rect class="cls-rect" x="{x0}" y="{top}" width="{width}" height="{height}">'
            f"<title>{titulo}</title></rect>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_curvas(itens: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-curve-candidates">']
    for item in itens:
        x0 = item.get("x0")
        top = item.get("top")
        width = item.get("width")
        height = item.get("height")
        if x0 is None or top is None or width is None or height is None:
            continue
        titulo = _title_forma(item, "curve_candidates")
        partes.append(
            f'    <rect class="cls-curve" x="{x0}" y="{top}" width="{width}" height="{height}">'
            f"<title>{titulo}</title></rect>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _metadata_xml(classificacao: dict[str, Any], pagina: dict[str, Any]) -> str:
    meta = {
        "source": classificacao.get("source"),
        "file_name": classificacao.get("file_name"),
        "page_number": pagina.get("page_number"),
        "width": pagina.get("width"),
        "height": pagina.get("height"),
        "coordinate_system": pagina.get("coordinate_system"),
        "classification_params": classificacao.get("classification_params"),
        "stats": pagina.get("stats"),
    }
    return (
        "  <metadata>\n"
        f"    <nbr12721:vectorClassificationDebug>"
        f"{_escape_xml(json.dumps(meta, ensure_ascii=False))}"
        f"</nbr12721:vectorClassificationDebug>\n"
        "  </metadata>"
    )


def _legenda_svg(width: float, height: float, mostrar_axis_aligned: bool) -> str:
    x0 = max(8.0, width - 145.0)
    y0 = 8.0
    entradas = [
        ("Contorno candidato", "cls-wall", "#00cccc", False),
        ("Diagonal", "cls-diagonal", "#cc6600", False),
        ("Carimbo/legenda", "cls-titleblock", "#999999", False),
        ("Texto denso", "cls-text-near", "#ddaa00", False),
        ("Curta", "cls-short", "#ff9999", False),
        ("Fina/ponto", "cls-thin", "#ffcccc", False),
        ("Retangulo", "cls-rect", "#6633cc", False),
        ("Curva bbox", "cls-curve", "#cc2222", True),
    ]
    if mostrar_axis_aligned:
        entradas.insert(1, ("Eixo alinhado", "cls-axis", "#88ddff", False))

    altura = 14 + len(entradas) * 11
    partes = [f'  <g id="layer-legend" transform="translate({x0:.3f},{y0:.3f})">']
    partes.append(
        f'    <rect x="0" y="0" width="135" height="{altura}" fill="#ffffff" '
        f'stroke="#cccccc" stroke-width="0.5" opacity="0.92"/>'
    )
    for i, (rotulo, classe, cor, tracejado) in enumerate(entradas):
        y = 12 + i * 11
        extra = ' stroke-dasharray="2 2"' if tracejado else ""
        partes.append(
            f'    <line class="geo-legend-sample {classe}" x1="6" y1="{y}" x2="22" y2="{y}" '
            f'stroke="{cor}"{extra}/>'
        )
        partes.append(f'    <text class="geo-legend-text" x="28" y="{y}">{_escape_xml(rotulo)}</text>')
    partes.append("  </g>")
    return "\n".join(partes)


def _aplicar_limites_noise(classified: dict[str, list[dict[str, Any]]], max_noise: int) -> dict[str, list[dict[str, Any]]]:
    restante = max(0, max_noise)
    limitado: dict[str, list[dict[str, Any]]] = dict(classified)
    for bucket in _NOISE_BUCKETS:
        itens = list(classified.get(bucket) or [])
        if restante <= 0:
            limitado[bucket] = []
            continue
        limitado[bucket] = itens[:restante]
        restante -= len(limitado[bucket])
    return limitado


def gerar_svg_pagina_classificada(
    pagina: dict[str, Any],
    classificacao: dict[str, Any] | None = None,
    *,
    mostrar_axis_aligned: bool = False,
    limites: LimitesClassificacaoSvg | None = None,
) -> str:
    """Gera SVG interpretado de uma pagina classificada."""
    limites = limites or LimitesClassificacaoSvg()
    classificacao = classificacao or {}
    classified = dict(pagina.get("classified") or {})

    width = float(pagina.get("width") or 1)
    height = float(pagina.get("height") or 1)

    classified = _aplicar_limites_noise(classified, limites.max_noise)
    walls = list(classified.get("wall_candidates") or [])[: limites.max_wall_candidates]
    rects = list(classified.get("rect_candidates") or [])[: limites.max_rects]
    curves = list(classified.get("curve_candidates") or [])[: limites.max_curves]
    axis = list(classified.get("axis_aligned_segments") or []) if mostrar_axis_aligned else []

    camadas: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}pt" height="{height}pt" '
            f'viewBox="0 0 {width} {height}">'
        ),
        "  <style>",
        _STYLES,
        "  </style>",
        _metadata_xml(classificacao, pagina),
        f'  <rect class="geo-page" width="{width}" height="{height}"/>',
    ]

    if mostrar_axis_aligned:
        layer_id, classe = _BUCKET_LAYER["axis_aligned_segments"]
        camadas.append(_layer_linhas(layer_id, classe, "axis_aligned_segments", axis))

    camadas.append(_layer_curvas(curves))
    camadas.append(_layer_retangulos(rects))

    for bucket in _NOISE_BUCKETS:
        layer_id, classe = _BUCKET_LAYER[bucket]
        camadas.append(_layer_linhas(layer_id, classe, bucket, list(classified.get(bucket) or [])))

    layer_id, classe = _BUCKET_LAYER["wall_candidates"]
    camadas.append(_layer_linhas(layer_id, classe, "wall_candidates", walls))
    camadas.append(_legenda_svg(width, height, mostrar_axis_aligned))
    camadas.append("</svg>")

    return "\n".join(camadas) + "\n"


def gerar_svgs_classificacao(
    classificacao: dict[str, Any],
    *,
    mostrar_axis_aligned: bool = False,
    limites: LimitesClassificacaoSvg | None = None,
) -> list[tuple[int, str]]:
    """Retorna lista de (page_number, svg) para todas as paginas classificadas."""
    saida: list[tuple[int, str]] = []
    for pagina in classificacao.get("pages") or []:
        numero = int(pagina.get("page_number") or len(saida) + 1)
        saida.append(
            (
                numero,
                gerar_svg_pagina_classificada(
                    pagina,
                    classificacao=classificacao,
                    mostrar_axis_aligned=mostrar_axis_aligned,
                    limites=limites,
                ),
            )
        )
    return saida


def salvar_svgs_classificacao(
    classificacao: dict[str, Any],
    pasta_saida: str | Path,
    stem: str | None = None,
    *,
    mostrar_axis_aligned: bool = False,
    limites: LimitesClassificacaoSvg | None = None,
) -> list[Path]:
    """Grava SVGs interpretados por pagina e retorna caminhos gerados."""
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    stem_final = stem or _stem_classificacao(classificacao.get("file_name"))
    caminhos: list[Path] = []
    for numero, svg in gerar_svgs_classificacao(
        classificacao,
        mostrar_axis_aligned=mostrar_axis_aligned,
        limites=limites,
    ):
        destino = pasta / _nome_arquivo_svg(stem_final, numero)
        destino.write_text(svg, encoding="utf-8")
        caminhos.append(destino)
    return caminhos
