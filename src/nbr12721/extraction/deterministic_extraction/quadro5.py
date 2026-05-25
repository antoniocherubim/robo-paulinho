"""Preenchimento deterministico do Quadro V."""

from __future__ import annotations

from .identity import _montar_outras_indicacoes
from .patterns import RE_APTOS_POR_PAV


def _preencher_quadro5(dados: dict, texto: str) -> None:
    q5 = dados["quadro5"]
    proj = dados["projeto"]
    designacao = dados["quadro3"]["projetoPadrao"]["designacao"]

    q5["tipoEdificacao"] = designacao
    q5["dataAprovacao"] = proj["dataAprovacao"]
    q5["numPavimentos"] = (
        str(proj["numPavimentos"]) if proj["numPavimentos"] > 0 else ""
    )

    m_pav = RE_APTOS_POR_PAV.search(texto)
    q5["unidadesPorPav"] = f"{m_pav.group(1)} APTOS/PAV" if m_pav else ""

    partes_garagem: list[str] = []
    if proj["vagasComum"] > 0:
        partes_garagem.append(f"{proj['vagasComum']} vagas comuns")
    if proj["vagasAcessorio"] > 0:
        partes_garagem.append(f"{proj['vagasAcessorio']} vagas duplas")
    q5["garagens"] = "; ".join(partes_garagem)
    q5["outrasIndicacoes"] = _montar_outras_indicacoes(dados, texto)
