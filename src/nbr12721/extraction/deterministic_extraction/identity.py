"""Extracao de identificacao, local, responsaveis e incorporador."""

from __future__ import annotations

import re

from .base_fields import _texto_menciona_crea
from .patterns import (
    RE_CEP,
    RE_CORTE_MARCADOR_ADMIN,
    RE_EDIFICIO_LINHA,
    RE_EMAIL,
    RE_ENDERECO_OBRA,
    RE_INCORPORADOR_ROTULO,
    RE_LOCAL_OBRA,
    RE_LOGRADOURO,
    RE_NOME_EDIFICIO_ROTULO,
    RE_NOME_RESP_INVALIDO,
    RE_PAGOTTO,
    RE_PROCESSO_APROVACAO,
    RE_PROFISSAO_NOME,
    RE_PROFISSAO_SPLIT,
    RE_SITUADO,
    RE_TEL,
)
from .utils import _limpar_texto_campo, _normalizar_linha_ocr


def _eh_apenas_cidade_uf(texto: str) -> bool:
    limpo = _limpar_texto_campo(texto)
    return bool(
        re.fullmatch(
            r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \t]*[-/][A-Z]{2}",
            limpo,
            flags=re.IGNORECASE,
        )
    )


def _extrair_local_construcao(texto: str) -> str:
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        for padrao in (RE_LOCAL_OBRA, RE_ENDERECO_OBRA):
            m = padrao.search(linha_n)
            if m:
                valor = _limpar_texto_campo(m.group(1))
                if valor and not _eh_apenas_cidade_uf(valor):
                    return valor
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        m = RE_SITUADO.match(linha_n)
        if m:
            valor = _limpar_texto_campo(m.group(1))
            if valor and not _eh_apenas_cidade_uf(valor):
                return valor
    return ""


def _nome_candidato_invalido(nome: str) -> bool:
    return bool(RE_NOME_RESP_INVALIDO.search(nome))


def _nome_antes_profissao(linha: str, *, somente_engenheiro_arquiteto: bool = False) -> str:
    padrao = RE_PROFISSAO_NOME if somente_engenheiro_arquiteto else RE_PROFISSAO_SPLIT
    m = padrao.search(linha)
    if not m:
        return ""
    antes = _limpar_texto_campo(linha[: m.start()].strip(" -–—"))
    if not antes:
        return ""
    if _nome_candidato_invalido(antes):
        return ""
    palavras = [p for p in antes.split() if re.search(r"[A-Za-zÀ-ÿ]", p, re.IGNORECASE)]
    if len(palavras) < 2:
        return ""
    if re.fullmatch(
        r"(?:ENGENHEIR[OA]|ARQUITET[OA])(?:\s+CIVIL|\s+URBANISTA)?",
        antes,
        flags=re.IGNORECASE,
    ):
        return ""
    return antes


def _extrair_responsavel_nome(texto: str, crea: str = "") -> str:
    if _texto_menciona_crea(texto):
        for linha in texto.splitlines():
            if re.search(r"CREA", linha, re.IGNORECASE):
                nome = _nome_antes_profissao(
                    linha, somente_engenheiro_arquiteto=True
                )
                if nome:
                    return nome
        return ""
    for linha in texto.splitlines():
        if re.search(r"CAU", linha, re.IGNORECASE):
            nome = _nome_antes_profissao(linha)
            if nome:
                return nome
    return ""


def _extrair_responsavel_endereco(texto: str) -> str:
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        if not RE_LOGRADOURO.search(linha_n):
            continue
        if (
            RE_CEP.search(linha_n)
            or RE_TEL.search(linha_n)
            or RE_EMAIL.search(linha_n)
        ):
            return _limpar_texto_campo(linha_n)
    return ""


def _cortar_nome_incorporador(valor: str) -> str:
    cortado = valor
    m = RE_CORTE_MARCADOR_ADMIN.search(valor)
    if m:
        cortado = valor[: m.start()]
    return _limpar_texto_campo(cortado.strip(" -–—"))


def _extrair_incorporador_nome(texto: str) -> str:
    for linha in texto.splitlines():
        m = RE_INCORPORADOR_ROTULO.search(linha)
        if m:
            nome = _cortar_nome_incorporador(m.group(1))
            if nome:
                return nome
    for linha in texto.splitlines():
        m = RE_PAGOTTO.search(linha)
        if m:
            nome = _cortar_nome_incorporador(m.group(1))
            if nome:
                return nome
    return ""


def _extrair_nome_edificio(texto: str, designacao: str = "") -> str:
    designacao_norm = designacao.upper().strip()

    def _aceito(nome: str) -> bool:
        if not nome:
            return False
        if nome.upper().startswith("RESIDENCIAL MULTIFAMILIAR"):
            return False
        if designacao_norm and nome.upper() in designacao_norm:
            return False
        return True

    for linha in texto.splitlines():
        m = RE_NOME_EDIFICIO_ROTULO.search(linha)
        if m:
            nome = _limpar_texto_campo(m.group(1))
            if _aceito(nome):
                return nome
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        if linha_n.upper().startswith("EDIFICAÇÃO") or linha_n.upper().startswith(
            "EDIFICACAO"
        ):
            continue
        m = RE_EDIFICIO_LINHA.match(linha_n)
        if m:
            nome = _limpar_texto_campo(m.group(1))
            if _aceito(nome):
                return nome
    return ""


def _extrair_processo_aprovacao(texto: str) -> str:
    m = RE_PROCESSO_APROVACAO.search(texto)
    if not m:
        return ""
    return _limpar_texto_campo(f"Processo Aprovação nº {m.group(1)}")


def _montar_outras_indicacoes(dados: dict, texto: str) -> str:
    partes: list[str] = []
    processo = _extrair_processo_aprovacao(texto)
    if processo:
        partes.append(processo)
    alvara = dados["projeto"].get("numAlvara", "")
    if alvara:
        partes.append(f"Alvará {alvara}")
    local = dados["projeto"].get("localConstrucao", "")
    if local:
        partes.append(f"Local: {local}")
    return "; ".join(partes)
