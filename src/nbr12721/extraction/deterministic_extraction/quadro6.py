"""Preenchimento deterministico conservador do Quadro VI (equipamentos)."""

from __future__ import annotations

import re

_MAX_DETALHES = 180
_RE_TAGS_ELEVADOR = re.compile(r"\bELEVADOR\d+\b", re.IGNORECASE)


def _candidato_equipamento_valido(candidato: dict) -> bool:
    return bool(str(candidato.get("nome", "")).strip())


def _extrair_tags_elevador(linhas: list[str]) -> list[str]:
    tags: list[str] = []
    vistos: set[str] = set()
    for linha in linhas:
        for match in _RE_TAGS_ELEVADOR.finditer(linha):
            tag = match.group(0).upper()
            if tag in vistos:
                continue
            vistos.add(tag)
            tags.append(tag)

    def _ordem(tag: str) -> int:
        numero = re.search(r"\d+", tag)
        return int(numero.group()) if numero else 0

    tags.sort(key=_ordem)
    return tags


def _montar_detalhes_elevador(linhas: list[str]) -> str:
    tags = _extrair_tags_elevador(linhas)
    if tags:
        return f"{'/'.join(tags)} citados"
    return linhas[0][: _MAX_DETALHES].rstrip() if linhas else ""


def _montar_detalhes_gas(_linhas: list[str]) -> str:
    return "Instalação de gás citada no memorial"


def _montar_detalhes_generico(_nome: str, linhas: list[str]) -> str:
    return linhas[0][: _MAX_DETALHES].rstrip() if linhas else ""


def _agregar_equipamentos_por_nome(candidatos: list[dict]) -> list[dict]:
    linhas_por_nome: dict[str, list[str]] = {}
    for candidato in candidatos:
        nome = candidato["nome"]
        linha = str(candidato.get("linha", candidato.get("detalhes", ""))).strip()
        if not linha:
            continue
        bucket = linhas_por_nome.setdefault(nome, [])
        if linha not in bucket:
            bucket.append(linha)

    itens: list[dict] = []
    for nome, linhas in linhas_por_nome.items():
        if nome == "Elevador":
            detalhes = _montar_detalhes_elevador(linhas)
        elif nome == "Instalação de gás":
            detalhes = _montar_detalhes_gas(linhas)
        else:
            detalhes = _montar_detalhes_generico(nome, linhas)
        if len(detalhes) > _MAX_DETALHES:
            detalhes = detalhes[:_MAX_DETALHES].rstrip()
        itens.append(
            {
                "nome": nome,
                "tipo": "",
                "acabamento": "",
                "detalhes": detalhes,
            }
        )
    return itens


def _preencher_quadro6(dados: dict, texto: str) -> None:
    """Preenche quadro6.equipamentos a partir de candidatos estruturados conservadores."""
    from ...documents.pdf_processing import extrair_candidatos_equipamentos

    candidatos = extrair_candidatos_equipamentos(texto)
    candidatos = [c for c in candidatos if _candidato_equipamento_valido(c)]
    itens = _agregar_equipamentos_por_nome(candidatos)
    if itens:
        dados["quadro6"]["equipamentos"] = itens
