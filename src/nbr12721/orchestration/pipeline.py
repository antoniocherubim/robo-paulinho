"""Orquestracao do pipeline NBR 12721:2006."""
import glob
import json
import logging
import os
import sys

from ..settings.config import (
    ARQ_AUDITORIA_PLANILHA_JSON,
    ARQ_DADOS_JSON,
    ARQ_PLANILHA_SAIDA,
    ARQ_RESUMOS_LOTES,
    ARQ_TEXTO_EXTRAIDO,
    ARQ_TEXTO_FILTRADO,
    ARQ_VALIDACAO_JSON,
    AUDITORIA_PLANILHA,
    PASTA_DOCS,
    PASTA_SAIDA,
    PLANILHA,
    VALIDACAO_BLOQUEANTE,
    caminho_saida,
)
from ..documents.pdf_processing import iterar_texto_pdf_paginas, prefiltrar_texto
from ..extraction.deterministic_extraction import extrair_dados_deterministico
from ..integrations.cub import buscar_cub_sinduscon
from ..outputs.excel_writer import preencher_planilha
from ..outputs.formatacao import formatar_brl
from .pipeline_llm import extrair_dados_via_llm, tratar_erro_llm
from .pipeline_compare import carregar_texto_filtrado_cache, executar_comparacao_modos
from .pipeline_modes import (
    comparar_modos,
    somente_json,
    usar_extracao_deterministica,
    usar_fallback_llm,
    usar_texto_filtrado_cache,
)
from .pipeline_postprocess import preencher_cub_automatico, registrar_validacao_dados

logger = logging.getLogger(__name__)

__all__ = ["executar_pipeline"]


def _formatar_bloco_pagina(pdf, pagina, texto):
    nome = os.path.basename(pdf)
    return (
        f"\n\n{'=' * 40}\n"
        f"DOCUMENTO: {nome}\n"
        f"PAGINA: {pagina}\n"
        f"{'=' * 40}\n"
        f"{texto.strip()}\n"
    )

async def executar_pipeline():
    argv = sys.argv
    usar_deterministico = usar_extracao_deterministica(argv)
    usar_fallback = usar_fallback_llm(argv)
    json_only = somente_json(argv)
    modo_comparacao = comparar_modos(argv)
    cache_filtrado = usar_texto_filtrado_cache(argv)
    logger.info("=" * 60)
    logger.info("NBR 12721:2006 - PREENCHIMENTO AUTOMATICO")
    if modo_comparacao:
        logger.info("Modo: comparacao deterministico vs LLM (sem re-OCR)")
    elif usar_deterministico:
        logger.info("Modo: extrator deterministico (sem LLM)")
    else:
        logger.info("Powered by LLM multi-provider (Anthropic / OpenAI)")
    logger.info(
        "Flags: deterministico=%s | fallback_llm=%s | json_only=%s | "
        "comparar_modos=%s | texto_filtrado_cache=%s | skip_extracao=%s",
        usar_deterministico,
        usar_fallback,
        json_only,
        modo_comparacao,
        cache_filtrado,
        "--skip-extracao" in argv,
    )
    logger.info("=" * 60)

    if modo_comparacao:
        textos = carregar_texto_filtrado_cache()
        logger.info("Buscando informacoes CUB...")
        cub_info = buscar_cub_sinduscon()
        await executar_comparacao_modos(textos, cub_info)
        return

    if not os.path.exists(PLANILHA):
        logger.error("Planilha nao encontrada: %s", PLANILHA)
        sys.exit(1)
    logger.info("Planilha modelo: %s", PLANILHA)

    path_textos_extraidos = caminho_saida(ARQ_TEXTO_EXTRAIDO)
    path_textos_filtrados = caminho_saida(ARQ_TEXTO_FILTRADO)
    if cache_filtrado:
        textos = carregar_texto_filtrado_cache()
    elif "--skip-extracao" in argv and os.path.exists(path_textos_extraidos):
        with open(path_textos_extraidos, encoding="utf-8") as f:
            textos = f.read()
        logger.info("Usando cache de texto: %s (%s chars)", path_textos_extraidos, len(textos))
        logger.info("Aplicando pre-filtragem...")
        textos = prefiltrar_texto(textos)

        with open(path_textos_filtrados, "w", encoding="utf-8") as f:
            f.write(textos)
        logger.info("Filtrado salvo em: %s", path_textos_filtrados)
    else:
        pdfs = sorted(
            set(glob.glob(os.path.join(PASTA_DOCS, "*.pdf")))
            | set(glob.glob(os.path.join(PASTA_DOCS, "*.PDF")))
        )
        if not pdfs:
            os.makedirs(PASTA_DOCS, exist_ok=True)
            logger.error("Nenhum PDF em '%s/'", PASTA_DOCS)
            logger.error("Coloque: memorial descritivo, quadro de areas, plantas (PDF)")
            sys.exit(1)

        os.makedirs(PASTA_SAIDA, exist_ok=True)
        logger.info(
            "%s PDF(s) | Extraindo e filtrando em streaming (1 PDF, 1 pagina por vez)...",
            len(pdfs),
        )
        total_bruto = 0
        total_filtrado = 0
        total_paginas = 0

        with open(path_textos_extraidos, "w", encoding="utf-8") as bruto_f, open(
            path_textos_filtrados, "w", encoding="utf-8"
        ) as filtrado_f:
            for pdf in pdfs:
                paginas_pdf = 0
                bruto_pdf = 0
                filtrado_pdf = 0
                logger.info("Processando PDF: %s", os.path.basename(pdf))
                for pagina, texto_pagina in iterar_texto_pdf_paginas(pdf):
                    bloco = _formatar_bloco_pagina(pdf, pagina, texto_pagina)
                    bruto_f.write(bloco)
                    bruto_f.flush()
                    total_bruto += len(bloco)
                    total_paginas += 1
                    paginas_pdf += 1
                    bruto_pdf += len(bloco)

                    bloco_filtrado = prefiltrar_texto(bloco, verbose=False)
                    if bloco_filtrado.strip():
                        filtrado_f.write(bloco_filtrado)
                        filtrado_f.write("\n\n")
                        filtrado_f.flush()
                        total_filtrado += len(bloco_filtrado)
                        filtrado_pdf += len(bloco_filtrado)
                logger.info(
                    "PDF finalizado: %s | paginas_extraidas=%s | bruto=%s chars | filtrado=%s chars",
                    os.path.basename(pdf),
                    paginas_pdf,
                    bruto_pdf,
                    filtrado_pdf,
                )

        if total_bruto <= 0:
            logger.error("Nenhum texto extraido dos PDFs")
            sys.exit(1)

        with open(path_textos_filtrados, encoding="utf-8") as f:
            textos = f.read()
        if not textos.strip():
            logger.error("Nenhum texto relevante apos filtragem")
            sys.exit(1)

        logger.info(
            "Extraidos %s pagina(s) | bruto=%s chars (%s) | filtrado=%s chars (%s)",
            total_paginas,
            total_bruto,
            path_textos_extraidos,
            total_filtrado,
            path_textos_filtrados,
        )

    logger.info("Total filtrado disponivel: %s chars", len(textos))

    logger.info("Buscando informacoes CUB...")
    cub_info = buscar_cub_sinduscon()
    if cub_info and cub_info.get("valores"):
        logger.info("CUB disponivel: %s tipo(s) | mes=%s", len(cub_info["valores"]), cub_info.get("mesAno", "?"))
    else:
        logger.warning("CUB indisponivel; quadro3.valorCub pode permanecer vazio")

    if usar_deterministico:
        logger.info("Extraindo dados em modo deterministico (sem LLM)...")
        dados = extrair_dados_deterministico(textos)
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        with open(caminho_saida(ARQ_RESUMOS_LOTES), "w", encoding="utf-8") as f:
            f.write("(modo deterministico: resumo LLM nao gerado)\n")
    else:
        try:
            dados = await extrair_dados_via_llm(textos, cub_info)
        except RuntimeError as e:
            tratar_erro_llm(e)
            sys.exit(1)

    preencher_cub_automatico(dados, cub_info)

    resultado_validacao = registrar_validacao_dados(dados, cub_info)

    if usar_deterministico and usar_fallback and not resultado_validacao["ok"]:
        logger.warning("Validacao deterministica falhou; tentando fallback LLM...")
        try:
            dados = await extrair_dados_via_llm(textos, cub_info)
        except RuntimeError as e:
            logger.error("Fallback LLM falhou: %s", e)
            sys.exit(1)

        preencher_cub_automatico(dados, cub_info)
        resultado_validacao = registrar_validacao_dados(dados, cub_info)
        logger.info(
            "Fallback LLM concluido; validacao final ok=%s score=%.4f",
            resultado_validacao["ok"],
            resultado_validacao["score"],
        )

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_dados_json = caminho_saida(ARQ_DADOS_JSON)
    with open(caminho_dados_json, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    logger.info("Dados extraidos salvos: %s", caminho_dados_json)

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

    if json_only:
        logger.info("Modo --json-only: planilha nao sera preenchida.")
        return

    if VALIDACAO_BLOQUEANTE and not resultado_validacao["ok"]:
        logger.error("Validacao bloqueante falhou; planilha nao sera preenchida.")
        return

    logger.info("Preenchendo planilha...")
    path_planilha_saida = caminho_saida(ARQ_PLANILHA_SAIDA)
    preencher_planilha(dados, PLANILHA, path_planilha_saida)

    if AUDITORIA_PLANILHA:
        try:
            from ..outputs.excel_audit import auditar_planilha_preenchida

            resultado_auditoria = auditar_planilha_preenchida(dados, path_planilha_saida)
            path_auditoria = caminho_saida(ARQ_AUDITORIA_PLANILHA_JSON)
            with open(path_auditoria, "w", encoding="utf-8") as f:
                json.dump(resultado_auditoria, f, ensure_ascii=False, indent=2)
            logger.info(
                "Auditoria planilha salva: %s | ok=%s | celulas=%s",
                path_auditoria,
                resultado_auditoria.get("ok"),
                resultado_auditoria.get("celulas_verificadas"),
            )
            if resultado_auditoria.get("erro"):
                logger.warning(
                    "Auditoria planilha com erro: %s",
                    resultado_auditoria["erro"],
                )
            elif resultado_auditoria.get("divergencias"):
                logger.warning("Divergencias auditoria planilha:")
                for item in resultado_auditoria["divergencias"]:
                    logger.warning("  - %s (%s)", item["celula"], item["campo"])
        except Exception as exc:
            logger.exception(
                "Auditoria planilha falhou com excecao inesperada; pipeline continua: %s",
                exc,
            )

    logger.info("=" * 50)
    logger.info("CONCLUIDO")
    logger.info("=" * 50)
    logger.info("Arquivos em '%s/':", PASTA_SAIDA)
    logger.info("  - %s", ARQ_PLANILHA_SAIDA)
    logger.info("  - %s", ARQ_DADOS_JSON)
    logger.info("  - %s", ARQ_VALIDACAO_JSON)
    if AUDITORIA_PLANILHA:
        logger.info("  - %s", ARQ_AUDITORIA_PLANILHA_JSON)
    logger.info("Abra no Excel e pressione Ctrl+Shift+F9")
