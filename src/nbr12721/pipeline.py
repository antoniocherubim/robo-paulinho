"""Orquestracao do pipeline NBR 12721:2006."""
import glob
import json
import logging
import os
import sys

from .config import (
    ARQ_DADOS_JSON,
    ARQ_PLANILHA_SAIDA,
    ARQ_RESPOSTA_BRUTA,
    ARQ_RESUMOS_LOTES,
    ARQ_TEXTO_EXTRAIDO,
    ARQ_TEXTO_FILTRADO,
    LIMITE_CHARS_PROMPT_FINAL,
    PASTA_DOCS,
    PASTA_SAIDA,
    PLANILHA,
    caminho_saida,
)
from .cub import buscar_cub_sinduscon, formatar_cub_contexto
from .excel_writer import preencher_planilha
from .formatacao import formatar_brl
from .llm import chamar_llm
from .pdf_processing import (
    dividir_lotes_documentos,
    extrair_texto_pdf,
    prefiltrar_texto,
    separar_documentos,
)
from .prompts import PROMPT_EXTRAIR, PROMPT_RESUMIR_LOTE
from .serialization import compactar_resumos, parsear_json

logger = logging.getLogger(__name__)

__all__ = ["executar_pipeline"]


def _extrair_evidencias_criticas(textos, limite_chars=12000):
    marcador_inicio = "EVIDENCIAS CRITICAS EXTRAIDAS DO TEXTO ORIGINAL:"
    marcador_fim = "\n\nTEXTO FILTRADO COMPLEMENTAR:"
    inicio = textos.find(marcador_inicio)
    if inicio < 0:
        return ""

    fim = textos.find(marcador_fim, inicio)
    if fim < 0:
        fim = len(textos)

    evidencias = textos[inicio:fim].strip()
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


async def executar_pipeline():
    logger.info("=" * 60)
    logger.info("NBR 12721:2006 - PREENCHIMENTO AUTOMATICO")
    logger.info("Powered by LLM multi-provider (Anthropic / OpenAI)")
    logger.info("=" * 60)

    if not os.path.exists(PLANILHA):
        logger.error("Planilha nao encontrada: %s", PLANILHA)
        sys.exit(1)
    logger.info("Planilha modelo: %s", PLANILHA)

    pdfs = sorted(
        set(glob.glob(os.path.join(PASTA_DOCS, "*.pdf")))
        | set(glob.glob(os.path.join(PASTA_DOCS, "*.PDF")))
    )
    if not pdfs:
        os.makedirs(PASTA_DOCS, exist_ok=True)
        logger.error("Nenhum PDF em '%s/'", PASTA_DOCS)
        logger.error("Coloque: memorial descritivo, quadro de areas, plantas (PDF)")
        sys.exit(1)

    path_textos_extraidos = caminho_saida(ARQ_TEXTO_EXTRAIDO)
    path_textos_filtrados = caminho_saida(ARQ_TEXTO_FILTRADO)
    if "--skip-extracao" in sys.argv and os.path.exists(path_textos_extraidos):
        with open(path_textos_extraidos, encoding="utf-8") as f:
            textos = f.read()
        logger.info("Usando cache de texto: %s (%s chars)", path_textos_extraidos, len(textos))
    else:
        logger.info("%s PDF(s) | Extraindo texto (pdfplumber + OCR)...", len(pdfs))
        textos = ""
        for pdf in pdfs:
            t = extrair_texto_pdf(pdf)
            if t:
                textos += (
                    f"\n\n{'=' * 40}\nDOCUMENTO: {os.path.basename(pdf)}\n{'=' * 40}\n{t}"
                )

        if not textos.strip():
            logger.error("Nenhum texto extraido dos PDFs")
            sys.exit(1)

        os.makedirs(PASTA_SAIDA, exist_ok=True)
        with open(path_textos_extraidos, "w", encoding="utf-8") as f:
            f.write(textos)
        logger.info("Total bruto: %s chars (salvo em %s)", len(textos), path_textos_extraidos)

    logger.info("Aplicando pre-filtragem...")
    textos = prefiltrar_texto(textos)

    with open(path_textos_filtrados, "w", encoding="utf-8") as f:
        f.write(textos)
    logger.info("Filtrado salvo em: %s", path_textos_filtrados)
    logger.info("Total filtrado disponivel: %s chars", len(textos))

    cub_info = buscar_cub_sinduscon()
    cub_ctx = formatar_cub_contexto(cub_info)

    resumos_lotes = await _resumir_lotes_documentos(textos)
    texto_resumido = compactar_resumos(resumos_lotes)
    evidencias_criticas = _extrair_evidencias_criticas(textos)
    if evidencias_criticas:
        texto_resumido = (
            f"{evidencias_criticas}\n\n"
            f"RESUMO CONSOLIDADO DOS LOTES:\n{texto_resumido}"
        )
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
        logger.error("LLM nao disponivel")
        logger.error("Instale: pip install anthropic openai claude-agent-sdk")
        logger.error("Ou configure Claude CLI: npm install -g @anthropic-ai/claude-code")
        sys.exit(1)

    logger.info("Processando resposta JSON...")
    try:
        dados = parsear_json(resposta)
    except json.JSONDecodeError as e:
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        with open(caminho_saida(ARQ_RESPOSTA_BRUTA), "w", encoding="utf-8") as f:
            f.write(resposta)
        logger.error("Erro JSON: %s | Resposta salva em %s", e, caminho_saida(ARQ_RESPOSTA_BRUTA))
        sys.exit(1)

    if cub_info and cub_info.get("valores"):
        q3 = dados.setdefault("quadro3", {})
        if not q3.get("valorCub"):
            pp = dados.get("projeto", {}).get("projetoPadrao", {})
            pp3 = q3.get("projetoPadrao", {})
            candidatos = [
                str(pp3.get("padrao", "")).strip().upper(),
                "CSL-8" if pp.get("CS") else "",
                "R4-N" if pp.get("R") else "",
                "R1-N" if pp.get("R") else "",
            ]
            tipo = next((t for t in candidatos if t and t in cub_info["valores"]), "")
            if tipo:
                q3["valorCub"] = cub_info["valores"][tipo]
                q3.setdefault("sindicato", cub_info["sindicato"])
                q3.setdefault("mesCub", cub_info["mesAno"])
                logger.info(
                    "CUB preenchido automaticamente: %s = R$ %s (%s)",
                    tipo,
                    formatar_brl(q3["valorCub"]),
                    cub_info["mesAno"],
                )

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(caminho_saida(ARQ_DADOS_JSON), "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    inc = dados.get("incorporador", {})
    proj = dados.get("projeto", {})
    q1 = dados.get("quadro1", {}).get("pavimentos", [])
    q2 = dados.get("quadro2", {}).get("unidades", [])
    q3 = dados.get("quadro3", {})
    logger.info("=" * 50)
    logger.info("DADOS EXTRAIDOS")
    logger.info("=" * 50)
    logger.info("Incorporador: %s", inc.get("nome", "?"))
    logger.info("CNPJ: %s", inc.get("cnpj", "?"))
    logger.info("Edificio: %s", proj.get("nomeEdificio", "?"))
    logger.info("Pavimentos: %s tipo(s)", len(q1))
    logger.info("Unidades: %s tipo(s)", len(q2))
    if q3.get("valorCub"):
        logger.info(
            "CUB: R$ %s (%s — %s)",
            formatar_brl(q3["valorCub"]),
            q3.get("mesCub", "?"),
            q3.get("sindicato", "?"),
        )
    falta = dados.get("_dados_faltantes", [])
    if falta:
        logger.warning("Dados faltantes:")
        for item in falta:
            logger.warning("  - %s", item)

    logger.info("Preenchendo planilha...")
    path_planilha_saida = caminho_saida(ARQ_PLANILHA_SAIDA)
    preencher_planilha(dados, PLANILHA, path_planilha_saida)

    logger.info("=" * 50)
    logger.info("CONCLUIDO")
    logger.info("=" * 50)
    logger.info("Arquivos em '%s/':", PASTA_SAIDA)
    logger.info("  - %s", ARQ_PLANILHA_SAIDA)
    logger.info("  - %s", ARQ_DADOS_JSON)
    logger.info("Abra no Excel e pressione Ctrl+Shift+F9")
