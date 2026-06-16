"""Inventario geometrico/textual de PDFs arquitetonicos.

Esta camada e deliberadamente diagnostica: ela nao tenta preencher a NBR 12721,
apenas preserva texto e vetores com coordenadas para as proximas etapas.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


TOLERANCIA_ORIENTACAO = 0.5


def _arredondar(valor: Any, casas: int = 3) -> float | None:
    if valor is None:
        return None
    try:
        return round(float(valor), casas)
    except (TypeError, ValueError):
        return None


def _normalizar(valor: Any, total: float) -> float | None:
    num = _arredondar(valor, 6)
    if num is None or not total:
        return None
    return round(num / float(total), 6)


def _cor_para_lista(cor: Any) -> list[float] | None:
    if cor is None:
        return None
    if isinstance(cor, (list, tuple)):
        return [_arredondar(c, 6) for c in cor]
    return None


def classificar_orientacao_linha(
    x0: float,
    top0: float,
    x1: float,
    top1: float,
    tolerancia: float = TOLERANCIA_ORIENTACAO,
) -> str:
    """Classifica a orientacao usando coordenadas com origem no topo da pagina."""
    dx = abs(float(x1) - float(x0))
    dy = abs(float(top1) - float(top0))
    if dx <= tolerancia and dy <= tolerancia:
        return "ponto"
    if dy <= tolerancia:
        return "horizontal"
    if dx <= tolerancia:
        return "vertical"
    return "diagonal"


def _comprimento(x0: float, top0: float, x1: float, top1: float) -> float:
    return round(math.hypot(float(x1) - float(x0), float(top1) - float(top0)), 3)


def _bbox_basico(obj: dict[str, Any], page_width: float, page_height: float) -> dict[str, Any]:
    x0 = _arredondar(obj.get("x0"))
    x1 = _arredondar(obj.get("x1"))
    top = _arredondar(obj.get("top"))
    bottom = _arredondar(obj.get("bottom"))
    return {
        "x0": x0,
        "x1": x1,
        "top": top,
        "bottom": bottom,
        "cx": _arredondar((x0 + x1) / 2) if x0 is not None and x1 is not None else None,
        "cy": _arredondar((top + bottom) / 2) if top is not None and bottom is not None else None,
        "width": _arredondar(obj.get("width")),
        "height": _arredondar(obj.get("height")),
        "norm": {
            "x0": _normalizar(x0, page_width),
            "x1": _normalizar(x1, page_width),
            "top": _normalizar(top, page_height),
            "bottom": _normalizar(bottom, page_height),
        },
    }


def _serializar_texto(word: dict[str, Any], page_width: float, page_height: float) -> dict[str, Any]:
    item = _bbox_basico(word, page_width, page_height)
    item.update(
        {
            "text": str(word.get("text", "")),
            "upright": bool(word.get("upright", True)),
            "direction": word.get("direction"),
        }
    )
    return item


def _serializar_linha(line: dict[str, Any], page_width: float, page_height: float) -> dict[str, Any]:
    item = _bbox_basico(line, page_width, page_height)
    x0 = item["x0"] or 0.0
    x1 = item["x1"] or 0.0
    top = item["top"] or 0.0
    bottom = item["bottom"] if item["bottom"] is not None else top
    item.update(
        {
            "orientation": classificar_orientacao_linha(x0, top, x1, bottom),
            "length": _comprimento(x0, top, x1, bottom),
            "linewidth": _arredondar(line.get("linewidth")),
            "stroke": bool(line.get("stroke", False)),
            "fill": bool(line.get("fill", False)),
            "stroking_color": _cor_para_lista(line.get("stroking_color")),
            "non_stroking_color": _cor_para_lista(line.get("non_stroking_color")),
        }
    )
    return item


def _serializar_forma(obj: dict[str, Any], page_width: float, page_height: float) -> dict[str, Any]:
    item = _bbox_basico(obj, page_width, page_height)
    item.update(
        {
            "linewidth": _arredondar(obj.get("linewidth")),
            "stroke": bool(obj.get("stroke", False)),
            "fill": bool(obj.get("fill", False)),
            "stroking_color": _cor_para_lista(obj.get("stroking_color")),
            "non_stroking_color": _cor_para_lista(obj.get("non_stroking_color")),
            "point_count": len(obj.get("pts") or []),
        }
    )
    return item


def inventariar_pagina_pdf(pagina: Any, numero_pagina: int) -> dict[str, Any]:
    """Extrai palavras e elementos vetoriais compactos de uma pagina pdfplumber."""
    page_width = float(pagina.width)
    page_height = float(pagina.height)
    palavras = pagina.extract_words(x_tolerance=2, y_tolerance=2) or []
    linhas = getattr(pagina, "lines", []) or []
    retangulos = getattr(pagina, "rects", []) or []
    curvas = getattr(pagina, "curves", []) or []

    return {
        "page_number": numero_pagina,
        "width": _arredondar(page_width),
        "height": _arredondar(page_height),
        "coordinate_system": "pdfplumber_top_left_points",
        "texts": [_serializar_texto(w, page_width, page_height) for w in palavras],
        "lines": [_serializar_linha(l, page_width, page_height) for l in linhas],
        "rects": [_serializar_forma(r, page_width, page_height) for r in retangulos],
        "curves": [_serializar_forma(c, page_width, page_height) for c in curvas],
        "stats": {
            "texts": len(palavras),
            "lines": len(linhas),
            "rects": len(retangulos),
            "curves": len(curvas),
        },
    }


def inventariar_pdf(caminho_pdf: str | Path, max_paginas: int | None = None) -> dict[str, Any]:
    """Gera inventario geometrico de um PDF sem OCR."""
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - depende do ambiente local
        raise RuntimeError("pdfplumber e necessario para inventariar geometria de PDFs") from exc

    caminho = Path(caminho_pdf)
    with pdfplumber.open(str(caminho)) as pdf:
        paginas = pdf.pages[:max_paginas] if max_paginas else pdf.pages
        itens = [inventariar_pagina_pdf(pagina, i + 1) for i, pagina in enumerate(paginas)]

    return {
        "source": str(caminho),
        "file_name": caminho.name,
        "page_count": len(itens),
        "pages": itens,
    }


def salvar_inventario_pdf(
    caminho_pdf: str | Path,
    caminho_saida: str | Path,
    max_paginas: int | None = None,
) -> dict[str, Any]:
    """Inventaria um PDF e grava JSON UTF-8 indentado."""
    inventario = inventariar_pdf(caminho_pdf, max_paginas=max_paginas)
    saida = Path(caminho_saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(inventario, ensure_ascii=False, indent=2), encoding="utf-8")
    return inventario

