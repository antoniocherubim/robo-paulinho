"""Extracao deterministica de campos basicos do empreendimento."""

from __future__ import annotations

import re

from .patterns import (
    JANELA_LINHAS_DATA_CONTEXTO,
    PALAVRAS_DATA_CONTEXTO,
    PALAVRAS_PADRAO_R,
    RE_ALVARA,
    RE_AREA_TERRENO_AT,
    RE_CIDADE_UF_LINHA,
    RE_CNPJ_DIGITOS,
    RE_CNPJ_ROTULADO,
    RE_CONTEXTO_PROFISSIONAL,
    RE_CREA,
    RE_CREA_COLADO,
    RE_DATA,
    RE_DESIGNACAO,
    RE_LINHA_CIDADE_UF_REJEITADA,
    RE_PREFIXO_EVIDENCIA_ARQUIVO,
    RE_PROPRIEDADE_TERRENO,
    RE_TERRENO,
    RE_TERRENO_M2,
    UFS_BRASIL,
)
from .utils import _parse_numero_br

_RE_PREFIXO_OCR_LINHA_CIDADE = re.compile(r"^(?:\([^)]*\)\s*)+")
_PRIMEIRA_PALAVRA_CIDADE_PRESERVAR = frozenset(
    {"de", "do", "da", "dos", "das", "são", "sao", "rio", "foz", "belo", "porto", "campo"}
)


def _somente_digitos(texto: str) -> str:
    return "".join(RE_CNPJ_DIGITOS.findall(texto))


def _normalizar_cnpj(raw: str) -> str:
    """Normaliza CNPJ com OCR ruim para XX.XXX.XXX/XXXX-XX."""
    digitos = _somente_digitos(raw)
    if len(digitos) != 14:
        return ""
    base = digitos[:8]
    ordem = digitos[8:12]
    dv = digitos[12:14]
    return f"{base[:2]}.{base[2:5]}.{base[5:8]}/{ordem}-{dv}"


def _extrair_cnpj(texto: str) -> str:
    for m in RE_CNPJ_ROTULADO.finditer(texto):
        normalizado = _normalizar_cnpj(m.group(1))
        if normalizado:
            return normalizado
    for bloco in re.findall(
        r"CNPJ\s*([\d./-]{14,20})",
        texto,
        flags=re.IGNORECASE,
    ):
        normalizado = _normalizar_cnpj(bloco)
        if normalizado:
            return normalizado
    for padrao in (
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b"),
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}\d{4}-\d{2})\b"),
    ):
        m = padrao.search(texto)
        if m:
            normalizado = _normalizar_cnpj(m.group(1))
            if normalizado:
                return normalizado
    return ""


def _capitalizar_cidade(cidade: str) -> str:
    partes = cidade.strip().split()
    return " ".join(p.capitalize() for p in partes if p)


def _normalizar_cidade_uf(cidade: str, uf: str) -> str:
    return f"{_capitalizar_cidade(cidade)}-{uf.upper()}"


def _linha_eh_contexto_profissional(linha: str) -> bool:
    return bool(RE_CONTEXTO_PROFISSIONAL.search(linha))


def _linha_para_cidade_uf(linha: str) -> str:
    limpa = RE_PREFIXO_EVIDENCIA_ARQUIVO.sub("", linha.strip())
    return _RE_PREFIXO_OCR_LINHA_CIDADE.sub("", limpa)


def _limpar_cidade_candidata(cidade: str) -> str:
    """
    Remove prefixos OCR curtos (ex.: Acd) preservando cidades compostas reais
    (São Paulo, Rio de Janeiro, Belo Horizonte, Foz do Iguaçu).
    """
    partes = cidade.strip().split()
    if len(partes) <= 1:
        return cidade.strip()

    while partes:
        primeiro = partes[0]
        chave = primeiro.lower().replace("ã", "a").replace("á", "a")
        if chave in _PRIMEIRA_PALAVRA_CIDADE_PRESERVAR:
            break
        if re.fullmatch(r"[A-Za-z]{2,3}", primeiro):
            partes.pop(0)
            continue
        break
    return " ".join(partes)


def _cidade_uf_candidata_valida(cidade: str, uf: str) -> bool:
    cidade_limpa = _limpar_cidade_candidata(cidade)
    if len(cidade_limpa) < 4 or uf not in UFS_BRASIL:
        return False
    return True


def _extrair_cidade_uf(texto: str) -> str:
    for linha in texto.splitlines():
        linha_busca = _linha_para_cidade_uf(linha)
        if _linha_eh_contexto_profissional(linha_busca):
            continue
        if RE_LINHA_CIDADE_UF_REJEITADA.search(linha_busca):
            continue
        melhor: tuple[str, str] | None = None
        for m in RE_CIDADE_UF_LINHA.finditer(linha_busca):
            cidade = m.group(1).strip()
            uf = m.group(2).strip().upper()
            if not _cidade_uf_candidata_valida(cidade, uf):
                continue
            melhor = (cidade, uf)
        if melhor:
            cidade, uf = melhor
            return _normalizar_cidade_uf(_limpar_cidade_candidata(cidade), uf)
    return ""


def _pontuacao_numero_admin(valor: str) -> int:
    """Prefere numero/ano (ex. 2457/2023); penaliza OCR colado (245712029)."""
    v = re.sub(r"\s+", "", valor.strip())
    if not v:
        return -1
    score = 0
    if re.search(r"/20\d{2}", v):
        score += 25
    if re.match(r"^\d{1,6}/\d{4}$", v):
        score += 20
    elif "/" in v and len(v) <= 24:
        score += 12
    elif re.match(r"^\d{3,6}$", v):
        score += 8
    if len(v) >= 9 and "/" not in v:
        score -= 20
    if re.match(r"^\d+\.\d+\.\d+/", v):
        score += 15
    return score


def _data_valida(dia: str, mes: str, ano: str) -> bool:
    try:
        d, m, a = int(dia), int(mes), int(ano)
    except ValueError:
        return False
    return 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= a <= 2100


def _formatar_data(dia: str, mes: str, ano: str) -> str:
    return f"{int(dia):02d}/{int(mes):02d}/{ano}"


def _indices_linhas_com_contexto_data(linhas: list[str]) -> list[int]:
    return [
        i
        for i, linha in enumerate(linhas)
        if PALAVRAS_DATA_CONTEXTO.search(linha)
    ]


def _extrair_data_aprovacao(texto: str) -> str:
    linhas = texto.splitlines()
    candidatas_gerais: list[tuple[int, str]] = []
    melhor_contexto: tuple[int, int, int, str] | None = None

    anchors = _indices_linhas_com_contexto_data(linhas)

    for idx, linha in enumerate(linhas):
        for m in RE_DATA.finditer(linha):
            if not _data_valida(m.group(1), m.group(2), m.group(3)):
                continue
            data_fmt = _formatar_data(m.group(1), m.group(2), m.group(3))
            candidatas_gerais.append((idx, data_fmt))

            if not anchors:
                continue

            for anchor in anchors:
                if abs(idx - anchor) > JANELA_LINHAS_DATA_CONTEXTO:
                    continue
                depois_anchor = 0 if idx >= anchor else 1
                chave = (abs(idx - anchor), depois_anchor, idx)
                if melhor_contexto is None or chave < melhor_contexto[:3]:
                    melhor_contexto = (*chave, data_fmt)

    if melhor_contexto is not None:
        return melhor_contexto[3]
    if candidatas_gerais:
        return candidatas_gerais[0][1]
    return ""


def _extrair_num_alvara(texto: str) -> str:
    melhor_valor = ""
    melhor_pontuacao = -1
    for m in RE_ALVARA.finditer(texto):
        valor = re.sub(r"\s+", "", m.group(1))
        pontuacao = _pontuacao_numero_admin(valor)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_valor = valor
    if melhor_pontuacao < 0:
        return ""
    return melhor_valor


def _extrair_area_terreno(texto: str) -> float:
    for padrao in (RE_AREA_TERRENO_AT, RE_TERRENO):
        m = padrao.search(texto)
        if m:
            valor = _parse_numero_br(m.group(1))
            if valor > 0:
                return valor
    for m in RE_TERRENO_M2.finditer(texto):
        inicio = max(0, m.start() - 30)
        if RE_PROPRIEDADE_TERRENO.search(texto[inicio : m.start()]):
            continue
        valor = _parse_numero_br(m.group(1))
        if valor > 0:
            return valor
    return 0.0


def _detectar_padrao_r(texto: str) -> bool:
    return bool(PALAVRAS_PADRAO_R.search(texto))


def _limpar_designacao(frase: str) -> str:
    return re.sub(r"\s+", " ", frase.strip())


def _extrair_designacao(texto: str) -> str:
    m = RE_DESIGNACAO.search(texto)
    if m:
        return _limpar_designacao(m.group(1))
    for linha in texto.splitlines():
        if re.search(r"residencial", linha, re.IGNORECASE) and re.search(
            r"multifamiliar|vertical|\[rmv\]", linha, re.IGNORECASE
        ):
            trecho = re.search(
                r"(EDIFICA[CÇ][AÃ]O\s+.+?\[RMV\])",
                linha,
                re.IGNORECASE,
            )
            if trecho:
                return _limpar_designacao(trecho.group(1))
    return ""


def _normalizar_crea(raw: str) -> str:
    """Normaliza registro CREA com variantes OCR."""
    texto = raw.strip()
    if not texto:
        return ""

    m = RE_CREA.search(texto)
    if m:
        uf = m.group(1).upper()
        numero = m.group(2)
        sufixo = (m.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    m_colado = RE_CREA_COLADO.search(texto)
    if m_colado:
        uf = m_colado.group(1).upper()
        numero = m_colado.group(2)
        sufixo = (m_colado.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    compacto = re.sub(r"\s+", "", texto, flags=re.IGNORECASE)
    compacto = re.sub(r"^CREA", "", compacto, flags=re.IGNORECASE)
    m2 = re.match(r"^([A-Z]{2})-?(\d{4,6})([A-Z])?$", compacto, re.IGNORECASE)
    if m2:
        uf = m2.group(1).upper()
        numero = m2.group(2)
        sufixo = (m2.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    return ""


def _extrair_crea(texto: str) -> str:
    if not re.search(r"CREA", texto, re.IGNORECASE):
        return ""
    for linha in texto.splitlines():
        if re.search(r"CREA", linha, re.IGNORECASE):
            normalizado = _normalizar_crea(linha)
            if normalizado:
                return normalizado
    return _normalizar_crea(texto)


def _texto_menciona_crea(texto: str) -> bool:
    return bool(re.search(r"CREA", texto, re.IGNORECASE))
