"""Extracao deterministica de unidades, pavimentos totais e vagas."""

from __future__ import annotations

import re

from .patterns import (
    RE_APTOS_POR_PAV,
    RE_AREA_X_APTOS,
    RE_COBERTURA,
    RE_INTERVALO_PAV,
    RE_N_PAVIMENTOS,
    RE_QTD_APTOS,
    RE_TERREO,
    RE_VAGAS_COMUNS,
    RE_VAGAS_DUPLAS,
)
from .utils import _normalizar_linha_ocr, _parse_numero_br


def _formatar_area_designacao(area: float) -> str:
    texto = f"{area:.4f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _item_unidade_quadro2(area: float, qtd: int) -> dict:
    designacao = ""
    if area > 0:
        designacao = f"Apartamento tipo {_formatar_area_designacao(area)} m²"
    return {
        "designacao": designacao,
        "areaPrivCobPadrao": area,
        "areaPrivCobDifReal": 0,
        "areaPrivCobDifEquiv": 0,
        "areaComumNPCobPadrao": 0,
        "areaComumNPCobDifReal": 0,
        "areaComumNPCobDifEquiv": 0,
        "qtdUnidades": qtd,
        "outrasAreasPriv": 0,
        "areaTerrExcl": 0,
        "areaTerrComum": 0,
    }


def _coletar_unidades(texto: str) -> list[tuple[float, int]]:
    """Coleta pares (area, qtd) deduplicados; area 0 para APTOS sem metragem."""
    vistos: dict[tuple[float, int], None] = {}
    linhas_vistas: set[str] = set()

    for linha_raw in texto.splitlines():
        linha = _normalizar_linha_ocr(linha_raw)
        if not linha or linha in linhas_vistas:
            continue
        linhas_vistas.add(linha)

        teve_area_x = False
        for m in RE_AREA_X_APTOS.finditer(linha):
            teve_area_x = True
            area = round(_parse_numero_br(m.group("area")), 3)
            qtd = int(m.group("qtd"))
            if qtd > 0:
                vistos[(area, qtd)] = None

        if not teve_area_x and not RE_APTOS_POR_PAV.search(linha):
            for m in RE_QTD_APTOS.finditer(linha):
                qtd = int(m.group("qtd"))
                if qtd > 0:
                    vistos[(0.0, qtd)] = None

    pares = list(vistos.keys())
    qtds_com_area = {q for a, q in pares if a > 0}
    if qtds_com_area:
        pares = [(a, q) for a, q in pares if a > 0 or q not in qtds_com_area]
    return sorted(pares, key=lambda par: (par[0], par[1]))


def _extrair_unidades_quadro2(texto: str) -> list[dict]:
    pares_com_area = [(a, q) for a, q in _coletar_unidades(texto) if a > 0]
    if not pares_com_area:
        return [_item_unidade_quadro2(0, 1)]
    return [_item_unidade_quadro2(area, qtd) for area, qtd in pares_com_area]


def _extrair_qtd_unidades(texto: str) -> int:
    return sum(qtd for _, qtd in _coletar_unidades(texto))


def _extrair_num_pavimentos(texto: str) -> int:
    base = 0
    m_intervalo = RE_INTERVALO_PAV.search(texto)
    if m_intervalo:
        base = max(int(m_intervalo.group(1)), int(m_intervalo.group(2)))
    else:
        m_total = RE_N_PAVIMENTOS.search(texto)
        if m_total:
            base = int(m_total.group(1))

    if base == 0:
        return 0

    extra = 0
    if RE_TERREO.search(texto):
        extra += 1
    if RE_COBERTURA.search(texto):
        extra += 1
    return base + extra


def _extrair_vagas_comuns(texto: str) -> int:
    valores = [int(v) for v in RE_VAGAS_COMUNS.findall(texto)]
    return max(valores) if valores else 0


def _extrair_vagas_duplas(texto: str) -> int:
    valores = [int(v) for v in RE_VAGAS_DUPLAS.findall(texto)]
    return max(valores) if valores else 0


def _texto_menciona_vagas_comuns(texto: str) -> bool:
    return bool(re.search(r"VAGAS\s+COMUNS?", texto, re.IGNORECASE))


def _texto_menciona_vagas_duplas(texto: str) -> bool:
    return bool(re.search(r"VAGAS\s+DUPLAS?", texto, re.IGNORECASE))


def _texto_menciona_aptos(texto: str) -> bool:
    return bool(re.search(r"APTOS?|APARTAMENTOS?", texto, re.IGNORECASE))


def _quadro2_apenas_template(unidades: list[dict]) -> bool:
    if len(unidades) != 1:
        return False
    u = unidades[0]
    return not u.get("designacao") and u.get("areaPrivCobPadrao", 0) == 0
