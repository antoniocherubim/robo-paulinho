"""Geracao de SVG diagnostico a partir de JSONs de regioes detectadas."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

DEFAULT_MAX_REGIONS_SVG = 50_000
DEFAULT_MAX_REJECTED_SVG = 50_000

_STYLES = """
  .geo-page { fill: #ffffff; }
  .cls-region { stroke: #00cc88; stroke-width: 0.8; fill: #00cc88; fill-opacity: 0.15; }
  .cls-rejected { stroke: #ff6633; stroke-width: 0.6; fill: #ff6633; fill-opacity: 0.08; stroke-dasharray: 3 2; }
  .cls-centroid { fill: #333333; stroke: none; }
  .cls-label { fill: #111111; font-family: sans-serif; font-size: 5px; }
  .geo-legend-text { fill: #111111; font-family: sans-serif; font-size: 6px; }
  .geo-legend-sample { stroke-width: 1.2; }
""".strip()

_LABEL_CURTO = re.compile(r"^p\d+_([rx]\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class LimitesRegioesSvg:
    max_regions: int = DEFAULT_MAX_REGIONS_SVG
    max_rejected: int = DEFAULT_MAX_REJECTED_SVG


def _escape_xml(texto: str) -> str:
    return escape(str(texto), quote=False)


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


def _nome_arquivo_svg(stem: str, page_number: int) -> str:
    return f"{stem}.p{page_number:03d}.regioes.debug.svg"


def _label_curto(region_id: str) -> str:
    match = _LABEL_CURTO.match(region_id or "")
    if match:
        return match.group(1)
    if region_id and "_" in region_id:
        return region_id.split("_", 1)[-1]
    return region_id or ""


def _edge_source_counts(edges: dict[str, Any] | None) -> str:
    if not edges:
        return ""
    partes = []
    for lado in ("top", "right", "bottom", "left"):
        borda = edges.get(lado) or {}
        count = borda.get("source_count")
        if count is None and borda.get("source_indices"):
            count = len(borda["source_indices"])
        if count is not None:
            partes.append(f"{lado}:{count}")
    return ",".join(partes)


def _title_regiao(regiao: dict[str, Any]) -> str:
    bbox = regiao.get("bbox") or {}
    partes = [
        f"id={regiao.get('id', '')}",
        f"confidence={regiao.get('confidence', '')}",
        f"rejection_reason={regiao.get('rejection_reason', '')}",
        (
            f"bbox=({bbox.get('x0')},{bbox.get('top')})"
            f"-({bbox.get('x1')},{bbox.get('bottom')})"
        ),
        f"width={bbox.get('width', '')}",
        f"height={bbox.get('height', '')}",
        f"area_pdf_units={bbox.get('area_pdf_units', '')}",
        f"source={regiao.get('source', '')}",
    ]
    counts = _edge_source_counts(regiao.get("edges"))
    if counts:
        partes.append(f"edge_source_counts={counts}")
    return _escape_xml(" | ".join(str(p) for p in partes))


def _metadata_xml(
    regioes_doc: dict[str, Any],
    pagina: dict[str, Any],
    *,
    rendered_regions: int,
    rendered_rejected: int,
    limites: LimitesRegioesSvg,
) -> str:
    stats = pagina.get("stats") or {}
    meta = {
        "source": regioes_doc.get("source"),
        "file_name": regioes_doc.get("file_name"),
        "page_number": pagina.get("page_number"),
        "width": pagina.get("width"),
        "height": pagina.get("height"),
        "coordinate_system": pagina.get("coordinate_system"),
        "detection_strategy": pagina.get("detection_strategy"),
        "truncated": pagina.get("truncated"),
        "stats": {
            "grid_cells_checked": stats.get("grid_cells_checked"),
            "closed_cells_found": stats.get("closed_cells_found"),
            "candidate_regions": stats.get("candidate_regions"),
            "rejected_regions": stats.get("rejected_regions"),
            "rejected_regions_saved": stats.get("rejected_regions_saved"),
            "duplicate_regions": stats.get("duplicate_regions"),
        },
        "rendered_regions": rendered_regions,
        "rendered_rejected_regions": rendered_rejected,
        "max_regions": limites.max_regions,
        "max_rejected": limites.max_rejected,
    }
    return (
        "  <metadata>\n"
        f"    <nbr12721:regionDebug>{_escape_xml(json.dumps(meta, ensure_ascii=False))}</nbr12721:regionDebug>\n"
        "  </metadata>"
    )


def _layer_regioes(
    layer_id: str,
    classe: str,
    regioes: list[dict[str, Any]],
) -> str:
    partes = [f'  <g id="{layer_id}">']
    for regiao in regioes:
        bbox = regiao.get("bbox") or {}
        x0 = bbox.get("x0")
        top = bbox.get("top")
        width = bbox.get("width")
        height = bbox.get("height")
        if x0 is None or top is None or width is None or height is None:
            continue
        titulo = _title_regiao(regiao)
        partes.append(
            f'    <rect class="{classe}" x="{x0}" y="{top}" width="{width}" height="{height}">'
            f"<title>{titulo}</title></rect>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_centroides(regioes: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-centroids">']
    for regiao in regioes:
        centro = regiao.get("centroid") or {}
        cx = centro.get("x")
        cy = centro.get("y")
        if cx is None or cy is None:
            continue
        titulo = _title_regiao(regiao)
        partes.append(
            f'    <circle class="cls-centroid" cx="{cx}" cy="{cy}" r="2">'
            f"<title>{titulo}</title></circle>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _layer_labels(regioes: list[dict[str, Any]]) -> str:
    partes = ['  <g id="layer-labels">']
    for regiao in regioes:
        centro = regiao.get("centroid") or {}
        cx = centro.get("x")
        cy = centro.get("y")
        if cx is None or cy is None:
            continue
        label = _escape_xml(_label_curto(str(regiao.get("id", ""))))
        titulo = _title_regiao(regiao)
        partes.append(
            f'    <text class="cls-label" x="{cx}" y="{float(cy) - 3}">'
            f"<title>{titulo}</title>{label}</text>"
        )
    partes.append("  </g>")
    return "\n".join(partes)


def _legenda_svg(width: float, height: float) -> str:
    x0 = max(8.0, width - 130.0)
    y0 = 8.0
    entradas = [
        ("Regiao candidata", "cls-region", "#00cc88", False),
        ("Rejeitada", "cls-rejected", "#ff6633", True),
        ("Centroide", "cls-centroid", "#333333", False, True),
    ]
    altura = 14 + len(entradas) * 11
    partes = [f'  <g id="layer-legend" transform="translate({x0:.3f},{y0:.3f})">']
    partes.append(
        f'    <rect x="0" y="0" width="120" height="{altura}" fill="#ffffff" '
        f'stroke="#cccccc" stroke-width="0.5" opacity="0.92"/>'
    )
    for i, entrada in enumerate(entradas):
        rotulo, classe, cor, tracejado = entrada[0], entrada[1], entrada[2], entrada[3]
        is_circle = len(entrada) > 4 and entrada[4]
        y = 12 + i * 11
        if is_circle:
            partes.append(
                f'    <circle class="{classe}" cx="14" cy="{y - 2}" r="2" fill="{cor}"/>'
            )
        else:
            extra = ' stroke-dasharray="3 2"' if tracejado else ""
            partes.append(
                f'    <rect class="geo-legend-sample {classe}" x="6" y="{y - 4}" '
                f'width="16" height="6" stroke="{cor}" fill="{cor}" fill-opacity="0.2"{extra}/>'
            )
        partes.append(f'    <text class="geo-legend-text" x="28" y="{y}">{_escape_xml(rotulo)}</text>')
    partes.append("  </g>")
    return "\n".join(partes)


def gerar_svg_pagina_regioes(
    page: dict[str, Any],
    regioes_doc: dict[str, Any] | None = None,
    *,
    mostrar_rejeitadas: bool = True,
    mostrar_labels: bool = True,
    limites: LimitesRegioesSvg | None = None,
) -> str:
    """Gera SVG diagnostico de regioes de uma pagina."""
    limites = limites or LimitesRegioesSvg()
    regioes_doc = regioes_doc or {}

    width = float(page.get("width") or 1)
    height = float(page.get("height") or 1)

    regions = list(page.get("regions") or [])[: limites.max_regions]
    rejected = (
        list(page.get("rejected_regions") or [])[: limites.max_rejected]
        if mostrar_rejeitadas
        else []
    )

    todas_para_centroides = regions + rejected

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
        _metadata_xml(
            regioes_doc,
            page,
            rendered_regions=len(regions),
            rendered_rejected=len(rejected),
            limites=limites,
        ),
        f'  <rect class="geo-page" width="{width}" height="{height}"/>',
    ]

    if mostrar_rejeitadas:
        camadas.append(_layer_regioes("layer-rejected-regions", "cls-rejected", rejected))
    camadas.append(_layer_regioes("layer-regions", "cls-region", regions))
    camadas.append(_layer_centroides(todas_para_centroides))
    if mostrar_labels:
        camadas.append(_layer_labels(todas_para_centroides))
    camadas.append(_legenda_svg(width, height))
    camadas.append("</svg>")

    return "\n".join(camadas) + "\n"


def gerar_svgs_regioes(
    regioes_doc: dict[str, Any],
    *,
    mostrar_rejeitadas: bool = True,
    mostrar_labels: bool = True,
    limites: LimitesRegioesSvg | None = None,
) -> list[tuple[int, str]]:
    """Retorna lista de (page_number, svg) para todas as paginas."""
    saida: list[tuple[int, str]] = []
    for pagina in regioes_doc.get("pages") or []:
        numero = int(pagina.get("page_number") or len(saida) + 1)
        saida.append(
            (
                numero,
                gerar_svg_pagina_regioes(
                    pagina,
                    regioes_doc=regioes_doc,
                    mostrar_rejeitadas=mostrar_rejeitadas,
                    mostrar_labels=mostrar_labels,
                    limites=limites,
                ),
            )
        )
    return saida


def salvar_svgs_regioes(
    regioes_doc: dict[str, Any],
    pasta_saida: str | Path,
    stem: str | None = None,
    *,
    mostrar_rejeitadas: bool = True,
    mostrar_labels: bool = True,
    limites: LimitesRegioesSvg | None = None,
) -> list[Path]:
    """Grava SVGs de regioes por pagina e retorna caminhos gerados."""
    pasta = Path(pasta_saida)
    pasta.mkdir(parents=True, exist_ok=True)
    stem_final = stem or _stem_regioes(regioes_doc.get("file_name"))
    caminhos: list[Path] = []
    for numero, svg in gerar_svgs_regioes(
        regioes_doc,
        mostrar_rejeitadas=mostrar_rejeitadas,
        mostrar_labels=mostrar_labels,
        limites=limites,
    ):
        destino = pasta / _nome_arquivo_svg(stem_final, numero)
        destino.write_text(svg, encoding="utf-8")
        caminhos.append(destino)
    return caminhos
