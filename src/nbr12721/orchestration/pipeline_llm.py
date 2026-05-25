"""Fluxo LLM do pipeline NBR 12721."""
import json
import logging
import os

from ..settings.config import (
    ARQ_RESPOSTA_BRUTA,
    ARQ_RESUMOS_LOTES,
    LIMITE_CHARS_PROMPT_FINAL,
    PASTA_SAIDA,
    caminho_saida,
)
from ..documents.pdf_processing import dividir_lotes_documentos, separar_documentos
from ..extraction.prompts import PROMPT_EXTRAIR, PROMPT_RESUMIR_LOTE
from ..extraction.serialization import compactar_resumos, parsear_json
from ..integrations.cub import formatar_cub_contexto
from ..integrations.llm import chamar_llm

logger = logging.getLogger(__name__)

__all__ = [
    "extrair_dados_via_llm",
    "extrair_evidencias_criticas",
    "tratar_erro_llm",
]


def extrair_evidencias_criticas(textos, limite_chars=12000):
    marcador_inicio = "EVIDENCIAS CRITICAS EXTRAIDAS DO TEXTO ORIGINAL:"
    marcador_fim = "\n\nTEXTO FILTRADO COMPLEMENTAR:"
    evidencias_partes = []
    pos = 0

    while pos < len(textos):
        inicio = textos.find(marcador_inicio, pos)
        if inicio < 0:
            break
        fim = textos.find(marcador_fim, inicio)
        if fim < 0:
            fim = len(textos)
        trecho = textos[inicio:fim].strip()
        if trecho:
            if evidencias_partes:
                trecho = trecho.replace(marcador_inicio, "").strip()
            evidencias_partes.append(trecho)
        pos = fim

    evidencias = "\n".join(evidencias_partes).strip()
    if len(evidencias) <= limite_chars:
        return evidencias

    corte = evidencias.rfind("\n", 0, limite_chars)
    if corte < limite_chars * 0.7:
        corte = limite_chars
    return evidencias[:corte].rstrip()


async def _resumir_lotes_documentos(textos):
    documentos = separar_documentos(textos)
    lotes = dividir_lotes_documentos(documentos)
    if not lotes:
        return []

    logger.info("Resumindo %s lote(s) antes da extracao final...", len(lotes))
    resumos = []
    for i, lote in enumerate(lotes, start=1):
        logger.info("Lote %s/%s (%s chars)", i, len(lotes), len(lote))
        prompt = PROMPT_RESUMIR_LOTE.replace("{textos}", lote)
        resposta = await chamar_llm(prompt)
        if not resposta:
            raise RuntimeError(f"Falha ao resumir lote {i}")
        resumo_json = parsear_json(resposta)
        resumos.append(resumo_json)
    return resumos


async def extrair_dados_via_llm(textos: str, cub_info: dict | None) -> dict:
    cub_ctx = formatar_cub_contexto(cub_info)

    resumos_lotes = await _resumir_lotes_documentos(textos)
    texto_resumido = compactar_resumos(resumos_lotes)
    evidencias_criticas = extrair_evidencias_criticas(textos)
    if evidencias_criticas:
        texto_resumido = (
            f"{evidencias_criticas}\n\n"
            f"RESUMO CONSOLIDADO DOS LOTES:\n{texto_resumido}"
        )

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(caminho_saida(ARQ_RESUMOS_LOTES), "w", encoding="utf-8") as f:
        f.write(texto_resumido)
    logger.info("Resumo consolidado: %s chars", len(texto_resumido))

    if len(texto_resumido) > LIMITE_CHARS_PROMPT_FINAL:
        logger.warning(
            "Resumo ainda grande (%s chars), truncando para %s",
            len(texto_resumido),
            LIMITE_CHARS_PROMPT_FINAL,
        )
        texto_resumido = texto_resumido[:LIMITE_CHARS_PROMPT_FINAL]

    prompt_completo = PROMPT_EXTRAIR.replace("{textos}", texto_resumido).replace(
        "{cub_contexto}", cub_ctx
    )

    logger.info("Enviando consolidacao final para o LLM...")
    resposta = await chamar_llm(prompt_completo)

    if not resposta:
        raise RuntimeError("LLM nao disponivel")

    logger.info("Processando resposta JSON...")
    try:
        return parsear_json(resposta)
    except json.JSONDecodeError as e:
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        with open(caminho_saida(ARQ_RESPOSTA_BRUTA), "w", encoding="utf-8") as f:
            f.write(resposta)
        raise RuntimeError(f"Erro JSON da LLM: {e}") from e


def tratar_erro_llm(e: RuntimeError) -> None:
    logger.error("%s", e)
    if "LLM nao disponivel" in str(e):
        logger.error("Instale: pip install anthropic openai claude-agent-sdk")
        logger.error("Ou configure Claude CLI: npm install -g @anthropic-ai/claude-code")
