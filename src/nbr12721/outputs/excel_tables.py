"""Tabelas intermediarias (pandas) para preenchimento da planilha."""

from __future__ import annotations

import pandas as pd

CAMPOS_EQUIPAMENTO = ("nome", "tipo", "acabamento", "detalhes")
CAMPOS_ACABAMENTO = ("dependencia", "pisos", "paredes", "tetos", "outros")

_COLS_PAVIMENTO = [
    "nome",
    "areaPrivCobPadrao",
    "areaPrivCobDifReal",
    "areaPrivCobDifEquiv",
    "areaComumNPCobPadrao",
    "areaComumNPCobDifReal",
    "areaComumNPCobDifEquiv",
    "areaComumPCobPadrao",
    "areaComumPCobDifReal",
    "areaComumPCobDifEquiv",
    "qtdPavimentos",
]

_COLS_UNIDADE = [
    "designacao",
    "areaPrivCobPadrao",
    "areaPrivCobDifReal",
    "areaPrivCobDifEquiv",
    "areaComumNPCobPadrao",
    "areaComumNPCobDifReal",
    "areaComumNPCobDifEquiv",
    "qtdUnidades",
    "outrasAreasPriv",
    "areaTerrExcl",
    "areaTerrComum",
]


def _numero(valor) -> float:
    try:
        return float(valor) if valor else 0.0
    except (TypeError, ValueError):
        return 0.0


def linha_vazia(item: dict, campos: tuple[str, ...]) -> bool:
    if not isinstance(item, dict):
        return True
    for campo in campos:
        valor = item.get(campo)
        if isinstance(valor, str):
            if valor.strip():
                return False
        elif isinstance(valor, (int, float)):
            if valor != 0:
                return False
        elif valor:
            return False
    return True


def _pavimento_tem_conteudo(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if str(item.get("nome", "")).strip():
        return True
    campos_area = (
        "areaPrivCobPadrao",
        "areaPrivCobDifReal",
        "areaPrivCobDifEquiv",
        "areaComumNPCobPadrao",
        "areaComumPCobPadrao",
    )
    return any(_numero(item.get(c)) > 0 for c in campos_area)


def _unidade_tem_conteudo(item: dict) -> bool:
    if not isinstance(item, dict):
        return False
    if str(item.get("designacao", "")).strip():
        return True
    campos_area = (
        "areaPrivCobPadrao",
        "areaPrivCobDifReal",
        "areaComumNPCobPadrao",
        "outrasAreasPriv",
        "areaTerrExcl",
        "areaTerrComum",
    )
    return any(_numero(item.get(c)) > 0 for c in campos_area)


def _normalizar_pavimento(item: dict) -> dict:
    return {
        "nome": item.get("nome", ""),
        "areaPrivCobPadrao": _numero(item.get("areaPrivCobPadrao")),
        "areaPrivCobDifReal": _numero(item.get("areaPrivCobDifReal")),
        "areaPrivCobDifEquiv": _numero(item.get("areaPrivCobDifEquiv")),
        "areaComumNPCobPadrao": _numero(item.get("areaComumNPCobPadrao")),
        "areaComumNPCobDifReal": _numero(item.get("areaComumNPCobDifReal")),
        "areaComumNPCobDifEquiv": _numero(item.get("areaComumNPCobDifEquiv")),
        "areaComumPCobPadrao": _numero(item.get("areaComumPCobPadrao")),
        "areaComumPCobDifReal": _numero(item.get("areaComumPCobDifReal")),
        "areaComumPCobDifEquiv": _numero(item.get("areaComumPCobDifEquiv")),
        "qtdPavimentos": _numero(item.get("qtdPavimentos", 1)) or 1,
    }


def _normalizar_unidade(item: dict) -> dict:
    return {
        "designacao": item.get("designacao", ""),
        "areaPrivCobPadrao": _numero(item.get("areaPrivCobPadrao")),
        "areaPrivCobDifReal": _numero(item.get("areaPrivCobDifReal")),
        "areaPrivCobDifEquiv": _numero(item.get("areaPrivCobDifEquiv")),
        "areaComumNPCobPadrao": _numero(item.get("areaComumNPCobPadrao")),
        "areaComumNPCobDifReal": _numero(item.get("areaComumNPCobDifReal")),
        "areaComumNPCobDifEquiv": _numero(item.get("areaComumNPCobDifEquiv")),
        "qtdUnidades": _numero(item.get("qtdUnidades", 1)) or 1,
        "outrasAreasPriv": _numero(item.get("outrasAreasPriv")),
        "areaTerrExcl": _numero(item.get("areaTerrExcl")),
        "areaTerrComum": _numero(item.get("areaTerrComum")),
    }


def tabela_quadro1(dados: dict) -> pd.DataFrame:
    itens = dados.get("quadro1", {}).get("pavimentos", [])
    linhas = [
        _normalizar_pavimento(p)
        for p in itens
        if isinstance(p, dict) and _pavimento_tem_conteudo(p)
    ]
    if not linhas:
        return pd.DataFrame(columns=_COLS_PAVIMENTO)
    return pd.DataFrame(linhas, columns=_COLS_PAVIMENTO)


def tabela_quadro2(dados: dict) -> pd.DataFrame:
    itens = dados.get("quadro2", {}).get("unidades", [])
    linhas = [
        _normalizar_unidade(u)
        for u in itens
        if isinstance(u, dict) and _unidade_tem_conteudo(u)
    ]
    if not linhas:
        return pd.DataFrame(columns=_COLS_UNIDADE)
    return pd.DataFrame(linhas, columns=_COLS_UNIDADE)


def tabela_quadro6(dados: dict) -> pd.DataFrame:
    itens = dados.get("quadro6", {}).get("equipamentos", [])
    linhas = [eq for eq in itens if isinstance(eq, dict) and not linha_vazia(eq, CAMPOS_EQUIPAMENTO)]
    cols = list(CAMPOS_EQUIPAMENTO)
    if not linhas:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(linhas, columns=cols).fillna("")


def tabela_quadro7(dados: dict) -> pd.DataFrame:
    itens = dados.get("quadro7", {}).get("acabamentos", [])
    linhas = [ac for ac in itens if isinstance(ac, dict) and not linha_vazia(ac, CAMPOS_ACABAMENTO)]
    cols = list(CAMPOS_ACABAMENTO)
    if not linhas:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(linhas, columns=cols).fillna("")


def tabela_quadro8(dados: dict) -> pd.DataFrame:
    itens = dados.get("quadro8", {}).get("acabamentos", [])
    linhas = [ac for ac in itens if isinstance(ac, dict) and not linha_vazia(ac, CAMPOS_ACABAMENTO)]
    cols = list(CAMPOS_ACABAMENTO)
    if not linhas:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame(linhas, columns=cols).fillna("")
