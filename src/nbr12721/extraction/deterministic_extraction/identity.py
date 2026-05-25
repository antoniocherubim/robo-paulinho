"""Extracao de identificacao, local, responsaveis e incorporador."""

from __future__ import annotations

import re

from .base_fields import _pontuacao_numero_admin, _texto_menciona_crea
from .patterns import (
    RE_BLOCO_ADMINISTRATIVO,
    RE_CEP,
    RE_CORTE_MARCADOR_ADMIN,
    RE_CPF_CNPJ_DATA_NOME,
    linha_contem_cnpj,
    RE_EDIFICIO_LINHA,
    RE_EMAIL,
    RE_EMPRESA_JURIDICA,
    RE_ENDERECO_OBRA,
    RE_INCORPORADOR_ROTULO,
    RE_LOCAL_CABECALHO,
    RE_LOCAL_KEYWORDS,
    RE_LOCAL_OBRA,
    RE_LOGRADOURO,
    RE_LOTE,
    RE_MENCAO_ROTULO_INCORPORADOR,
    RE_NOME_EDIFICIO_ROTULO,
    RE_NOME_RESP_INVALIDO,
    RE_PROCESSO_APROVACAO,
    RE_PROFISSAO_NOME,
    RE_PROFISSAO_SPLIT,
    RE_SITUADO,
    RE_SITUADO_NO,
    RE_TAXA_PERCENTUAL_FINAL,
    RE_TEL,
)
from .utils import (
    _limpar_ruido_ocr_textual,
    _limpar_texto_campo,
    _normalizar_linha_ocr,
)


def _eh_apenas_cidade_uf(texto: str) -> bool:
    limpo = _limpar_texto_campo(texto)
    return bool(
        re.fullmatch(
            r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \t]*[-/][A-Z]{2}",
            limpo,
            flags=re.IGNORECASE,
        )
    )


def _local_candidato_invalido(valor: str) -> bool:
    if not valor or _eh_apenas_cidade_uf(valor):
        return True
    if RE_LOCAL_CABECALHO.search(valor) and not RE_LOCAL_KEYWORDS.search(valor):
        return True
    return False


def _limpar_local_obra(valor: str) -> str:
    limpo = _limpar_texto_campo(valor)
    limpo = RE_TAXA_PERCENTUAL_FINAL.sub("", limpo).strip(" ,;")
    limpo = re.sub(r",?\s*[°º]\s*,?", ", ", limpo)
    limpo = re.sub(r",\s*,", ", ", limpo)
    limpo = re.sub(r"\s+", " ", limpo).strip(" ,;")
    return _limpar_ruido_ocr_textual(limpo)


def _pontuacao_local_consolidado(valor: str) -> int:
    if not valor:
        return -1
    score = 0
    if RE_LOTE.search(valor):
        score += 12
    if RE_LOCAL_KEYWORDS.search(valor):
        score += 6
    if re.search(r"\bLOTE\s+\d", valor, re.IGNORECASE):
        score += 4
    lixo = len(re.findall(r"[—\-]{2,}|[^\w\s,./À-ÿ-]{2,}", valor, re.IGNORECASE))
    score -= lixo * 5
    score -= max(0, len(valor) - 180) // 20
    return score


def _consolidar_lote_situado(linhas: list[str], inicio: int) -> str:
    parte_lote = ""
    parte_situado = ""
    j_inicio = max(0, inicio - 2)
    for j in range(j_inicio, min(inicio + 4, len(linhas))):
        linha_n = _normalizar_linha_ocr(linhas[j])
        if _eh_apenas_cidade_uf(linha_n):
            continue
        if RE_LOTE.search(linha_n) and not parte_lote:
            parte_lote = _limpar_local_obra(linha_n)
        m_sit = RE_SITUADO_NO.search(linha_n)
        if m_sit:
            parte_situado = _limpar_local_obra(m_sit.group(1))
    if parte_lote and parte_situado:
        return _limpar_local_obra(f"{parte_lote}, {parte_situado}")
    if parte_lote:
        return parte_lote
    if parte_situado:
        return parte_situado
    return ""


def _limpar_prefixo_ocr_nome(valor: str) -> str:
    """Remove lixo OCR numerico/simbolico no inicio (ex.: '7 ACME' -> 'ACME')."""
    nome = _limpar_texto_campo(valor)
    nome = re.sub(r"^[\s\d|°º.:;\-*_]+", "", nome)
    while nome and not re.match(r"[A-Za-zÀ-ÿ]", nome):
        nome = nome[1:].lstrip()
    return nome.strip()


def _limpar_nome_incorporador(valor: str) -> str:
    nome = _cortar_nome_incorporador(valor)
    nome = _limpar_prefixo_ocr_nome(nome)
    nome = re.sub(r"\s+\d{10,}.*$", "", nome).strip()
    return _limpar_ruido_ocr_textual(nome)


def _extrair_local_construcao(texto: str) -> str:
    linhas = texto.splitlines()
    melhor_consolidado = ""
    melhor_pontuacao = -1
    for i, linha in enumerate(linhas):
        linha_n = _normalizar_linha_ocr(linha)
        if RE_LOTE.search(linha_n) or RE_SITUADO_NO.search(linha_n):
            consolidado = _consolidar_lote_situado(linhas, i)
            if not consolidado:
                continue
            pontuacao = _pontuacao_local_consolidado(consolidado)
            if pontuacao > melhor_pontuacao:
                melhor_pontuacao = pontuacao
                melhor_consolidado = consolidado
    if melhor_consolidado:
        return melhor_consolidado

    for i, linha in enumerate(linhas):
        linha_n = _normalizar_linha_ocr(linha)
        if not (
            RE_LOCAL_OBRA.search(linha_n)
            or RE_ENDERECO_OBRA.search(linha_n)
            or RE_LOCAL_CABECALHO.search(linha_n)
        ):
            continue
        for padrao in (RE_LOCAL_OBRA, RE_ENDERECO_OBRA):
            m = padrao.search(linha_n)
            if m:
                valor = _limpar_local_obra(m.group(1))
                if valor and not _local_candidato_invalido(valor):
                    return valor
        consolidado = _consolidar_lote_situado(linhas, i + 1)
        if consolidado:
            return consolidado

    for linha in linhas:
        linha_n = _normalizar_linha_ocr(linha)
        m = RE_SITUADO.match(linha_n)
        if m:
            valor = _limpar_local_obra(m.group(1))
            if valor and not _local_candidato_invalido(valor):
                return valor

    melhor_linha = ""
    melhor_pontuacao = -1
    for linha in linhas:
        linha_n = _normalizar_linha_ocr(linha)
        if not RE_LOCAL_KEYWORDS.search(linha_n):
            continue
        valor = _limpar_local_obra(linha_n)
        if not valor or _local_candidato_invalido(valor):
            continue
        pontuacao = _pontuacao_local_consolidado(valor)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_linha = valor
    return melhor_linha


def _nome_candidato_invalido(nome: str) -> bool:
    return bool(RE_NOME_RESP_INVALIDO.search(nome))


def _nome_antes_profissao(linha: str, *, somente_engenheiro_arquiteto: bool = False) -> str:
    padrao = RE_PROFISSAO_NOME if somente_engenheiro_arquiteto else RE_PROFISSAO_SPLIT
    m = padrao.search(linha)
    if not m:
        return ""
    antes = _limpar_prefixo_ocr_nome(linha[: m.start()].strip(" -–—"))
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


def _nome_parece_lixo(nome: str) -> bool:
    if not nome:
        return True
    if "*" in nome or "@" in nome:
        return True
    letras = len(re.findall(r"[A-Za-zÀ-ÿ]", nome, re.IGNORECASE))
    simbolos = len(re.findall(r"[^A-Za-zÀ-ÿ0-9\s]", nome))
    palavras = [p for p in nome.split() if re.search(r"[A-Za-zÀ-ÿ]", p, re.IGNORECASE)]
    if len(palavras) < 2 or letras < 8:
        return True
    if simbolos > letras * 0.15:
        return True
    curtas = sum(1 for p in palavras if len(p) <= 3)
    if curtas >= len(palavras) - 1:
        return True
    return False


def _pontuacao_legibilidade_nome(linha: str) -> tuple[int, int, int]:
    """Maior pontuacao = mais legivel (letras, -simbolos, -penalidades)."""
    limpo = _limpar_texto_campo(linha)
    if _nome_candidato_invalido(limpo):
        return (-1, 0, 0)
    if RE_CPF_CNPJ_DATA_NOME.search(limpo):
        return (-1, 0, 0)
    palavras = [p for p in limpo.split() if re.search(r"[A-Za-zÀ-ÿ]", p, re.IGNORECASE)]
    if len(palavras) < 2:
        return (-1, 0, 0)
    letras = len(re.findall(r"[A-Za-zÀ-ÿ]", limpo, re.IGNORECASE))
    simbolos = len(re.findall(r"[^A-Za-zÀ-ÿ0-9\s]", limpo))
    return (letras - simbolos * 2, letras, -len(palavras))


def _melhor_nome_linhas_anteriores(linhas: list[str], indice_crea: int) -> str:
    candidatos: list[tuple[tuple[int, int, int], str]] = []
    for offset in range(1, 4):
        idx = indice_crea - offset
        if idx < 0:
            break
        linha = linhas[idx]
        if re.search(r"CREA|CAU", linha, re.IGNORECASE):
            continue
        pontuacao = _pontuacao_legibilidade_nome(linha)
        if pontuacao[0] < 0:
            continue
        nome = _limpar_prefixo_ocr_nome(linha)
        candidatos.append((pontuacao, nome))
    if not candidatos:
        return ""
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return candidatos[0][1]


def _extrair_responsavel_nome(texto: str, crea: str = "") -> str:
    if _texto_menciona_crea(texto):
        linhas = texto.splitlines()
        for i, linha in enumerate(linhas):
            if not re.search(r"CREA", linha, re.IGNORECASE):
                continue
            nome = _nome_antes_profissao(linha, somente_engenheiro_arquiteto=True)
            if nome and not _nome_parece_lixo(nome):
                return _limpar_ruido_ocr_textual(nome)
            nome_melhor = _melhor_nome_linhas_anteriores(linhas, i)
            if nome_melhor:
                return _limpar_ruido_ocr_textual(nome_melhor)
        return ""
    for linha in texto.splitlines():
        if re.search(r"CAU", linha, re.IGNORECASE):
            nome = _nome_antes_profissao(linha)
            if nome:
                return _limpar_ruido_ocr_textual(nome)
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
            return _limpar_ruido_ocr_textual(linha_n)
    return ""


def _cortar_nome_incorporador(valor: str) -> str:
    cortado = valor
    m = RE_CORTE_MARCADOR_ADMIN.search(valor)
    if m:
        cortado = valor[: m.start()]
    return _limpar_texto_campo(cortado.strip(" -–—"))


def _nome_incorporador_aceito(linha: str, valor: str) -> bool:
    if not valor or len(valor) <= 2:
        return False
    if valor in (":", "-", "–", "—"):
        return False
    if RE_BLOCO_ADMINISTRATIVO.search(linha):
        return False
    return bool(RE_EMPRESA_JURIDICA.search(valor) or len(valor.split()) >= 2)


def _extrair_incorporador_por_rotulo(linhas: list[str]) -> str:
    for i, linha in enumerate(linhas):
        if RE_BLOCO_ADMINISTRATIVO.search(linha):
            continue
        m = RE_INCORPORADOR_ROTULO.search(linha)
        if m:
            nome = _limpar_nome_incorporador(m.group(1))
            if _nome_incorporador_aceito(linha, nome):
                return nome
        if not RE_MENCAO_ROTULO_INCORPORADOR.search(linha):
            continue
        for j in range(i + 1, min(i + 3, len(linhas))):
            prox = _limpar_texto_campo(linhas[j])
            if _nome_incorporador_aceito(linhas[j], prox):
                return _limpar_nome_incorporador(prox)
    return ""


def _extrair_incorporador_perto_cnpj(linhas: list[str]) -> str:
    for i, linha in enumerate(linhas):
        if not linha_contem_cnpj(linha):
            continue
        for j in range(max(0, i - 2), min(len(linhas), i + 3)):
            candidata = linhas[j]
            if RE_BLOCO_ADMINISTRATIVO.search(candidata):
                continue
            prox = _limpar_texto_campo(candidata)
            if RE_EMPRESA_JURIDICA.search(prox) and _nome_incorporador_aceito(
                candidata, prox
            ):
                return _limpar_nome_incorporador(prox)
    return ""


def _extrair_incorporador_nome(texto: str) -> str:
    linhas = texto.splitlines()
    por_rotulo = _extrair_incorporador_por_rotulo(linhas)
    if por_rotulo:
        return por_rotulo
    return _extrair_incorporador_perto_cnpj(linhas)


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
    melhor_numero = ""
    melhor_pontuacao = -1
    for m in RE_PROCESSO_APROVACAO.finditer(texto):
        numero = re.sub(r"\s+", "", m.group(1))
        pontuacao = _pontuacao_numero_admin(numero)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_numero = numero
    if melhor_pontuacao < 0:
        return ""
    return _limpar_texto_campo(f"Processo Aprovação nº {melhor_numero}")


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
