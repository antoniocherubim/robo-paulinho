"""Extracao do Quadro I: pavimentos e areas explicitas."""

from __future__ import annotations

import re

from .patterns import (
    NOME_COBERTURA,
    NOME_PAVIMENTO_TERREO,
    NOME_PAVIMENTOS_TIPO,
    RE_AREA_COBERTURA,
    RE_AREA_LAZER_COBERTA_TERREO,
    RE_AREA_LAZER_DESCOBERTA_TERREO,
    RE_AREA_PAV_TERREO,
    RE_INTERVALO_PAV,
    RE_PAV_TIPO_LINHA,
)
from .units import _coletar_unidades
from .utils import _parse_numero_br


def _item_pavimento_quadro1(
    nome: str,
    *,
    area_priv_cob_padrao: float = 0,
    area_comum_np_cob_padrao: float = 0,
    area_comum_p_cob_padrao: float = 0,
    qtd_pavimentos: int = 1,
) -> dict:
    return {
        "nome": nome,
        "areaPrivCobPadrao": area_priv_cob_padrao,
        "areaPrivCobDifReal": 0,
        "areaPrivCobDifEquiv": 0,
        "areaComumNPCobPadrao": area_comum_np_cob_padrao,
        "areaComumNPCobDifReal": 0,
        "areaComumNPCobDifEquiv": 0,
        "areaComumPCobPadrao": area_comum_p_cob_padrao,
        "areaComumPCobDifReal": 0,
        "areaComumPCobDifEquiv": 0,
        "qtdPavimentos": qtd_pavimentos,
    }


def _item_pavimento_quadro1_vazio() -> list[dict]:
    return [_item_pavimento_quadro1("")]


def _calcular_area_privativa_tipo_total(texto: str) -> float:
    """Soma area*qtd das unidades tipo; total do conjunto, nao area por pavimento."""
    return sum(
        area * qtd
        for area, qtd in _coletar_unidades(texto)
        if area > 0
    )


def _extrair_qtd_pavimentos_tipo(texto: str) -> int:
    max_qtd = 0
    for linha in texto.splitlines():
        if not RE_PAV_TIPO_LINHA.search(linha):
            continue
        for m in RE_INTERVALO_PAV.finditer(linha):
            max_qtd = max(max_qtd, int(m.group(1)), int(m.group(2)))
    return max_qtd


def _extrair_pavimento_tipo(texto: str) -> dict | None:
    area_total = _calcular_area_privativa_tipo_total(texto)
    qtd_tipo = _extrair_qtd_pavimentos_tipo(texto)
    if area_total <= 0 or qtd_tipo <= 0:
        return None
    return _item_pavimento_quadro1(
        NOME_PAVIMENTOS_TIPO,
        area_priv_cob_padrao=area_total,
        qtd_pavimentos=qtd_tipo,
    )


def _extrair_pavimento_terreo(texto: str) -> dict | None:
    coberta: float | None = None
    descoberta: float | None = None
    for m in RE_AREA_LAZER_COBERTA_TERREO.finditer(texto):
        coberta = _parse_numero_br(m.group(1))
    for m in RE_AREA_LAZER_DESCOBERTA_TERREO.finditer(texto):
        descoberta = _parse_numero_br(m.group(1))

    if coberta is not None or descoberta is not None:
        return _item_pavimento_quadro1(
            NOME_PAVIMENTO_TERREO,
            area_comum_p_cob_padrao=coberta or 0.0,
            area_comum_np_cob_padrao=descoberta or 0.0,
        )

    for m in RE_AREA_PAV_TERREO.finditer(texto):
        total = _parse_numero_br(m.group(1))
        if total > 0:
            return _item_pavimento_quadro1(
                NOME_PAVIMENTO_TERREO,
                area_comum_p_cob_padrao=total,
            )
    return None


def _extrair_pavimento_cobertura(texto: str) -> dict | None:
    for m in RE_AREA_COBERTURA.finditer(texto):
        area = _parse_numero_br(m.group(1))
        if area > 0:
            return _item_pavimento_quadro1(
                NOME_COBERTURA,
                area_priv_cob_padrao=area,
            )
    return None


def _extrair_pavimentos_quadro1(texto: str) -> list[dict]:
    pavimentos: list[dict] = []
    terreo = _extrair_pavimento_terreo(texto)
    if terreo:
        pavimentos.append(terreo)
    tipo = _extrair_pavimento_tipo(texto)
    if tipo:
        pavimentos.append(tipo)
    cobertura = _extrair_pavimento_cobertura(texto)
    if cobertura:
        pavimentos.append(cobertura)
    if not pavimentos:
        return _item_pavimento_quadro1_vazio()
    return pavimentos


def _quadro1_apenas_template(pavimentos: list[dict]) -> bool:
    if len(pavimentos) != 1:
        return False
    return not pavimentos[0].get("nome")


def _texto_menciona_pavimentos_ou_areas(texto: str) -> bool:
    return bool(
        re.search(
            r"PAV\.?\s*TIPO|PAVIMENTO\s+T[EÉ]RREO|\bT[EÉ]RREO\b|"
            r"COBERTURA|[AÁ]REA\s+PAVIMENTO",
            texto,
            re.IGNORECASE,
        )
    )
