"""Utilidades puras usadas pelos extratores deterministicos."""

from __future__ import annotations

import re

from .patterns import RE_PREFIXO_ARQUIVO_PDF

_UFS_BRASIL = frozenset(
    {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
)

_SUFIXOS_PRESERVADOS = frozenset(
    {
        "LTDA",
        "SA",
        "S/A",
        "S.A",
        "SPE",
        "EIRELI",
        "ME",
        "EPP",
        "INC",
        "CIA",
    }
) | _UFS_BRASIL

_RE_BORDA_INICIO_SIMBOLOS = re.compile(r"^[\s|*_\-.–—,;:]+")
_RE_VIRGULAS_REPETIDAS = re.compile(r",\s*,+")


def _parse_numero_br(valor: str) -> float:
    """Converte numero brasileiro (ex.: 8.958,97) para float."""
    limpo = valor.strip()
    if not limpo:
        return 0.0
    limpo = re.sub(r"\s+", "", limpo)
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    else:
        limpo = limpo.replace(",", "")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def _normalizar_linha_ocr(linha: str) -> str:
    return re.sub(r"\s+", " ", linha.strip())


def _limpar_texto_campo(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip())


def _token_preservado(segmento: str) -> bool:
    """True se o segmento final deve ser mantido (societario, UF, etc.)."""
    nucleo = re.sub(r"[^\wÀ-ÿ/]", "", segmento, flags=re.IGNORECASE).upper()
    if not nucleo:
        return False
    if nucleo in _SUFIXOS_PRESERVADOS:
        return True
    if "/" in segmento.upper():
        partes = [p for p in re.split(r"[/\s]+", segmento.upper()) if p]
        partes = [re.sub(r"[^\w]", "", p) for p in partes]
        if partes and all(p in _SUFIXOS_PRESERVADOS for p in partes if p):
            return True
    return False


def _segmento_e_ruido_ocr_final(segmento: str) -> bool:
    """
    Indica se o ultimo segmento (apos virgula) e lixo formal de OCR.
    Segmentos com digitos ou tokens preservados nunca sao ruído.
    """
    bruto = segmento.strip()
    if not bruto:
        return True
    if re.search(r"\d", bruto):
        return False
    if _token_preservado(bruto):
        return False
    if re.fullmatch(r"[\s|*_\-.–—,;:.]+", bruto):
        return True
    letras = re.sub(r"[^\wÀ-ÿ]", "", bruto, flags=re.IGNORECASE)
    if not letras:
        return True
    if len(letras) > 3:
        return False
    if letras.isascii() and letras.islower():
        return True
    if len(letras) <= 1:
        return True
    return False


def _remover_sufixo_simbolico(texto: str) -> str:
    """Remove sufixo de simbolos soltos; preserva ponto apos letras (ex.: LTDA.)."""
    limpo = texto.rstrip()
    while limpo:
        if limpo[-1] in "|*_-–—,;:":
            limpo = limpo[:-1].rstrip()
            continue
        if limpo[-1] == ".":
            if len(limpo) > 1 and re.match(
                r"[A-Za-zÀ-ÿ0-9]", limpo[-2], re.IGNORECASE
            ):
                break
            limpo = limpo[:-1].rstrip()
            continue
        if limpo[-1] in "-–—":
            limpo = limpo[:-1].rstrip()
            continue
        break
    return limpo


def _remover_bordas_simbolicas(texto: str) -> str:
    """Remove prefixos/sufixos compostos apenas por simbolos e pontuacao solta."""
    limpo = _RE_BORDA_INICIO_SIMBOLOS.sub("", texto).strip()
    return _remover_sufixo_simbolico(limpo)


def _remover_segmentos_finais_ruido(texto: str) -> str:
    """Remove tokens finais suspeitos apos virgula; para quando o ultimo segmento e valido."""
    resultado = texto
    while "," in resultado:
        partes = [p.strip() for p in resultado.split(",")]
        if len(partes) <= 1:
            break
        if not _segmento_e_ruido_ocr_final(partes[-1]):
            break
        partes.pop()
        resultado = ", ".join(p for p in partes if p)
        if not resultado:
            break
    return resultado


def _remover_prefixo_arquivo_pdf(valor: str) -> str:
    """Remove prefixo conservador [arquivo.pdf] no inicio da string."""
    return RE_PREFIXO_ARQUIVO_PDF.sub("", valor)


def _limpar_ruido_ocr_textual(valor: str) -> str:
    """
    Saneamento operacional pos-OCR: simbolos isolados, virgulas finais e
    tokens finais curtos sem significado. Nao altera numeros nem corrige conteudo.
    """
    if not valor:
        return ""
    texto = _remover_prefixo_arquivo_pdf(_limpar_texto_campo(valor))
    texto = _remover_bordas_simbolicas(texto)
    texto = _RE_VIRGULAS_REPETIDAS.sub(", ", texto)
    texto = texto.strip().rstrip(",")
    texto = _remover_segmentos_finais_ruido(texto)
    texto = _remover_bordas_simbolicas(texto)
    return _limpar_texto_campo(texto).rstrip(",")
