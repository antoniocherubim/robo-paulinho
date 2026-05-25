"""Utilidades puras usadas pelos extratores deterministicos."""

from __future__ import annotations

import re


def _parse_numero_br(valor: str) -> float:
    """Converte numero brasileiro (ex.: 8.958,97) para float."""
    limpo = valor.strip()
    if not limpo:
        return 0.0
    limpo = re.sub(r"\s+", "", limpo)
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    else:
        limpo = limpo.replace(",", "")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def _normalizar_linha_ocr(linha: str) -> str:
    return re.sub(r"\s+", " ", linha.strip())


def _limpar_texto_campo(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip())
