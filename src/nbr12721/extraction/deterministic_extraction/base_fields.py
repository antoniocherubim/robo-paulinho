"""Extracao deterministica de campos basicos do empreendimento."""

from __future__ import annotations

import re

from .patterns import (
    JANELA_LINHAS_DATA_CONTEXTO,
    PALAVRAS_DATA_CONTEXTO,
    PALAVRAS_PADRAO_R,
    RE_ALVARA,
    RE_CIDADE_UF_LINHA,
    RE_CNPJ_DIGITOS,
    RE_CONTEXTO_PROFISSIONAL,
    RE_CREA,
    RE_CREA_COLADO,
    RE_DATA,
    RE_DESIGNACAO,
    RE_TERRENO,
)
from .utils import _parse_numero_br


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
    padroes = [
        re.compile(
            r"CNPJ\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
            re.IGNORECASE,
        ),
        re.compile(
            r"CNPJ\s*(\d{2}\.?\d{3}\.?\d{3}\d{4}-?\d{2})",
            re.IGNORECASE,
        ),
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b"),
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}\d{4}-\d{2})\b"),
    ]
    for padrao in padroes:
        m = padrao.search(texto)
        if m:
            normalizado = _normalizar_cnpj(m.group(1))
            if normalizado:
                return normalizado
    blocos = re.findall(
        r"CNPJ\s*([\d./-]{14,20})",
        texto,
        flags=re.IGNORECASE,
    )
    for bloco in blocos:
        normalizado = _normalizar_cnpj(bloco)
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


def _extrair_cidade_uf(texto: str) -> str:
    for linha in texto.splitlines():
        if _linha_eh_contexto_profissional(linha):
            continue
        for m in RE_CIDADE_UF_LINHA.finditer(linha):
            cidade = m.group(1).strip()
            uf = m.group(2).strip()
            if len(cidade) >= 3 and uf.isalpha():
                return _normalizar_cidade_uf(cidade, uf)
    return ""


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
    m = RE_ALVARA.search(texto)
    if not m:
        return ""
    valor = re.sub(r"\s+", "", m.group(1))
    return valor.replace(" ", "")


def _extrair_area_terreno(texto: str) -> float:
    m = RE_TERRENO.search(texto)
    if not m:
        return 0.0
    return _parse_numero_br(m.group(1))


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
