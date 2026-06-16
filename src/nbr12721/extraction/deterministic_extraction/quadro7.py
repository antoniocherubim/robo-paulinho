"""Preenchimento deterministico conservador do Quadro VII (acabamentos privativos)."""

from __future__ import annotations

from .quadro8 import (
    _candidato_para_item_acabamento,
    _deduplicar_itens_acabamento,
)


def _candidato_quadro7_valido(candidato: dict) -> bool:
    if candidato.get("quadro") != "quadro7":
        return False
    if not str(candidato.get("dependencia", "")).strip():
        return False
    materiais = candidato.get("materiais")
    if not isinstance(materiais, list) or not materiais:
        return False
    if not str(candidato.get("linha", "")).strip():
        return False
    return True


def _preencher_quadro7(dados: dict, texto: str) -> None:
    """Preenche quadro7.acabamentos a partir de candidatos estruturados conservadores."""
    from ...documents.pdf_processing import extrair_candidatos_acabamentos

    candidatos = extrair_candidatos_acabamentos(texto)
    itens = [
        _candidato_para_item_acabamento(c)
        for c in candidatos
        if _candidato_quadro7_valido(c)
    ]
    itens = _deduplicar_itens_acabamento(itens)
    if itens:
        dados["quadro7"]["acabamentos"] = itens
