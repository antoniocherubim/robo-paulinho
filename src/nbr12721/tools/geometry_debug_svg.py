"""Geracao de SVG diagnostico a partir de inventarios geometricos de PDF."""
from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_MAX_LINES = 50_000
DEFAULT_MAX_CURVES = 20_000
DEFAULT_MAX_TEXTS = 20_000
MAX_TEXTO_VISUAL = 20

_CLASSES_LINHA = {
    "horizontal": "geo-line-horizontal",
    "vertical": "geo-line-vertical",
    "diagonal": "geo-line-diagonal",
}

_STYLES = """
  .geo-page { fill: #ffffff; }
  .geo-text { fill: #222222; font-family: sans-serif; font-size: 4px; }
  .geo-line-horizontal { stroke: #0066cc; stroke-width: 0.4; fill: none; }
  .geo-line-vertical { stroke: #228833; stroke-width: 0.4; fill: none; }
  .geo-line-diagonal { stroke: #cc6600; stroke-width: 0.4; fill: none; }
  .geo-rect { stroke: #6633cc; stroke-width: 0.5; fill: none; }
  .geo-curve { stroke: #cc2222; stroke-width: 0.5; fill: none; stroke-dasharray: 2 2; }
  .geo-legend-text { fill: #111111; font-family: sans-serif; font-size: 6px; }
  .geo-legend-sample { stroke-width: 1.2; fill: none; }
""".strip()


@dataclass(frozen=True)
class LimitesCamada:
    max_lines: int = DEFAULT_MAX_LINES
    max_curves: int = DEFAULT_MAX_CURVES
    max_texts: int = DEFAULT_MAX_TEXTS


def _truncar_texto_visual(texto: str, limite: int = MAX_TEXTO_VISUAL) -> str:
    texto = str(texto)
    if len(texto) <= limite:
        return texto
    return f"{texto[: limite - 3]}..."


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


def _nome_arquivo_svg(stem: str, page_number: int) -> str:
    return f"{stem}.p{page_number:03d}.debug.svg"


def _metadata_xml(
  inventario: dict[str, Any],
  pagina: dict[str, Any],
) -> str:
    stats = pagina.get("stats") or {}
    meta = {
        "source": inventario.get("source"),
        "file_name": inventario.get("file_name"),
        "page_number": pagina.get("page_number"),
        "width": pagina.get("width"),
        "height": pagina.get("height"),
        "coordinate_system": pagina.get("coordinate_system"),
        "stats": stats,
    }
    return (
        "  <metadata>\n"
        f"    <nbr12721:geometryDebug>{escape(json.dumps(meta, ensure_ascii=False))}</nbr12721:geometryDebug>\n"
        "  </metadata>"
    )


def _legenda_svg(width: float, height: float) -> str:
    x0 = max(8.0, width - 118.0)
    y0 = 8.0
    linhas = [
        ("Texto", "geo-text", None, "#222222"),
        ("Horizontal", "geo-line-horizontal", "geo-legend-sample", "#0066cc"),
        ("Vertical", "geo-line-vertical", "geo-legend-sample", "#228833"),
        ("Diagonal", "geo-line-diagonal", "geo-legend-sample", "#cc6600"),
        ("Retangulo", "geo-rect", "geo-legend-sample", "#6633cc"),
        ("Curva (bbox)", "geo-curve", "geo-legend-sample", "#cc2222"),
    ]
    partes = [f'  <g id="layer-legend" transform="translate({x0:.3f},{y0:.3f})">']
    partes.append('    <rect x="0" y="0" width="110" height="78" fill="#ffffff" stroke="#cccccc" stroke-width="0.5" opacity="0.92"/>')
    for i, (rotulo, classe, sample_class, cor) in enumerate(linhas):
        y = 12 + i * 11
        if sample_class:
            extra = ' stroke-dasharray="2 2"' if classe == "geo-curve" else ""
            partes.append(
                f'    <line class="{sample_class} {classe}" x1="6" y1="{y}" x2="22" y2="{y}" stroke="{cor}"{extra}/>'
            )
        else:
            partes.append(f'    <text class="geo-legend-text" x="6" y="{y}">T</text>')
        partes.append(f'    <text class="geo-legend-text" x="28" y="{y}">{escape(rotulo)}</text>')
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_rects(rects: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-rects">']
    for item in rects:
        x0 = item.get("x0")
        top = item.get("top")
        width = item.get("width")
        height = item.get("height")
        if x0 is None or top is None or width is None or height is None:
            continue
        partes.append(
            f'    <rect class="geo-rect" x="{x0}" y="{top}" width="{width}" height="{height}"/>'
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_curves(curves: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-curves">']
    for item in curves:
        x0 = item.get("x0")
        top = item.get("top")
        width = item.get("width")
        height = item.get("height")
        if x0 is None or top is None or width is None or height is None:
            continue
        partes.append(
            f'    <rect class="geo-curve" x="{x0}" y="{top}" width="{width}" height="{height}"/>'
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_lines(lines: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-lines">']
    for item in lines:
        orientacao = item.get("orientation") or "diagonal"
        if orientacao == "ponto":
            continue
        classe = _CLASSES_LINHA.get(orientacao, "geo-line-diagonal")
        x0 = item.get("x0")
        top = item.get("top")
        x1 = item.get("x1")
        bottom = item.get("bottom")
        if x0 is None or top is None or x1 is None or bottom is None:
            continue
        partes.append(
            f'    <line class="{classe}" x1="{x0}" y1="{top}" x2="{x1}" y2="{bottom}"/>'
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_texts(texts: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-texts">']
    for item in texts:
        texto = str(item.get("text", ""))
        if not texto:
            continue
        x0 = item.get("x0")
        top = item.get("top")
        if x0 is None or top is None:
            continue
        visual = _truncar_texto_visual(texto)
        partes.append(
            f'    <text class="geo-text" x="{x0}" y="{top}">'
            f"<title>{escape(texto)}</title>{escape(visual)}</text>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def gerar_svg_pagina(
    pagina: dict[str, Any],
    inventario: dict[str, Any] | None = None,
    limites: LimitesCamada | None = None,
) -> str:
    """Gera SVG diagnostico de uma pagina do inventario."""
    limites = limites or LimitesCamada()
    inventario = inventario or {}

    width = float(pagina.get("width") or 1)
    height = float(pagina.get("height") or 1)

    rects = list(pagina.get("rects") or [])
    curves = list(pagina.get("curves") or [])[: limites.max_curves]
    lines = list(pagina.get("lines") or [])[: limites.max_lines]
    texts = list(pagina.get("texts") or [])[: limites.max_texts]

    blocos = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}pt" height="{height}pt" '
            f'viewBox="0 0 {width} {height}">'
        ),
        "  <style>",
        _STYLES,
        "  </style>",
        _metadata_xml(inventario, pagina),
        f'  <rect class="geo-page" width="{width}" height="{height}"/>',
        _layer_rects(rects),
        _layer_curves(curves),
        _layer_lines(lines),
        _layer_texts(texts),
        _legenda_svg(width, height),
        "</svg>",
    ]
    return "\n".join(blocos) + "\n"


def gerar_svgs_inventario(
    inventario: dict[str, Any],
    limites: LimitesCamada | None = None,
) -> list[tuple[int, str]]:
    """Retorna lista de (page_number, svg) para todas as paginas."""
    saida: list[tuple[int, str]] = []
    for pagina in inventario.get("pages") or []:
        numero = int(pagina.get("page_number") or len(saida) + 1)
        saida.append((numero, gerar_svg_pagina(pagina, inventario=inventario, limites=limites)))
    return saida


def salvar_svgs_inventario(
    inventario: dict[str, Any],
    pasta_saida: str | Path,
    stem: str | None = None,
    limites: LimitesCamada | None = None,
) -> list[Path]:
    """Grava SVGs por pagina e retorna caminhos gerados."""
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    stem_final = stem or _stem_inventario(inventario.get("file_name"))
    caminhos: list[Path] = []
    for numero, svg in gerar_svgs_inventario(inventario, limites=limites):
        destino = pasta / _nome_arquivo_svg(stem_final, numero)
        destino.write_text(svg, encoding="utf-8")
        caminhos.append(destino)
    return caminhos
