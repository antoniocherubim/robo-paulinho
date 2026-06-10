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
from ..documents.pdf_processing import (
    MARCADOR_CANDIDATOS_VII_VIII,
    MARCADOR_EVIDENCIAS_VI_VIII,
    MARCADOR_QUADRO_VI,
    MARCADOR_QUADRO_VII,
    MARCADOR_QUADRO_VIII,
    dividir_lotes_documentos,
    extrair_candidatos_acabamentos_estruturados,
    extrair_evidencias_acabamentos_equipamentos,
    separar_documentos,
)

_MARCADORES_SUBSECAO_ORDEM = (
    MARCADOR_QUADRO_VI,
    MARCADOR_QUADRO_VII,
    MARCADOR_QUADRO_VIII,
)
from ..extraction.prompts import PROMPT_ENRIQUECER_PATCH, PROMPT_EXTRAIR, PROMPT_RESUMIR_LOTE
from ..extraction.field_responsibility import campos_llm_editaveis
from ..extraction.serialization import compactar_resumos, parsear_json
from ..integrations.cub import formatar_cub_contexto
from ..integrations.llm import chamar_llm

logger = logging.getLogger(__name__)

__all__ = [
    "extrair_dados_via_llm",
    "extrair_evidencias_criticas",
    "gerar_patch_llm",
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


def _parse_bloco_vi_viii(bloco: str) -> tuple[list[str], dict[str, list[str]]]:
    """Retorna marcadores de subsecao presentes (ordem) e linhas por marcador."""
    marcadores_presentes: list[str] = []
    linhas_por_marcador: dict[str, list[str]] = {}
    marcador_atual: str | None = None

    for linha in bloco.splitlines():
        texto = linha.strip()
        if not texto or texto == MARCADOR_EVIDENCIAS_VI_VIII:
            continue
        if texto in _MARCADORES_SUBSECAO_ORDEM:
            marcador_atual = texto
            if marcador_atual not in marcadores_presentes:
                marcadores_presentes.append(marcador_atual)
                linhas_por_marcador[marcador_atual] = []
            continue
        if marcador_atual is not None:
            linhas_por_marcador[marcador_atual].append(linha)

    return marcadores_presentes, linhas_por_marcador


def _reconstituir_bloco_vi_viii(
    marcadores_presentes: list[str],
    linhas_por_marcador: dict[str, list[str]],
) -> str:
    partes = [MARCADOR_EVIDENCIAS_VI_VIII]
    for marcador in marcadores_presentes:
        partes.append("")
        partes.append(marcador)
        partes.extend(linhas_por_marcador.get(marcador, []))
    return "\n".join(partes).strip()


def _truncar_bloco_vi_viii(bloco: str, limite_chars: int) -> str:
    """Trunca linhas de conteudo preservando cabecalho global e de subsecoes."""
    bloco = bloco.strip()
    if len(bloco) <= limite_chars:
        return bloco

    marcadores_presentes, linhas_por_marcador = _parse_bloco_vi_viii(bloco)
    if not marcadores_presentes:
        return bloco[:limite_chars]

    linhas_vazias = {marcador: [] for marcador in marcadores_presentes}
    esqueleto = _reconstituir_bloco_vi_viii(marcadores_presentes, linhas_vazias)
    if len(esqueleto) >= limite_chars:
        return esqueleto

    linhas = {
        marcador: list(linhas_por_marcador.get(marcador, []))
        for marcador in marcadores_presentes
    }
    while True:
        reconstruido = _reconstituir_bloco_vi_viii(marcadores_presentes, linhas)
        if len(reconstruido) <= limite_chars:
            return reconstruido

        removido = False
        for marcador in _MARCADORES_SUBSECAO_ORDEM:
            secao = linhas.get(marcador, [])
            if secao:
                secao.pop()
                removido = True
                break
        if not removido:
            return esqueleto


def _separar_evidencias_e_candidatos(bloco: str) -> tuple[str, str]:
    """Separa bloco bruto VI-VIII do bloco de candidatos estruturados."""
    bloco = bloco.strip()
    if not bloco:
        return "", ""
    idx = bloco.find(MARCADOR_CANDIDATOS_VII_VIII)
    if idx < 0:
        return bloco, ""
    raw = bloco[:idx].strip()
    candidatos = bloco[idx:].strip()
    return raw, candidatos


def _truncar_bloco_candidatos(bloco: str, limite_chars: int) -> str:
    """Remove linhas de candidato do fim; preserva cabecalho."""
    bloco = bloco.strip()
    if len(bloco) <= limite_chars:
        return bloco
    if not bloco.startswith(MARCADOR_CANDIDATOS_VII_VIII):
        return bloco[:limite_chars]

    linhas = bloco.splitlines()
    cabecalho = linhas[0]
    itens = [linha for linha in linhas[1:] if linha.strip().startswith("-")]
    while itens:
        reconstruido = "\n".join([cabecalho, *itens]).strip()
        if len(reconstruido) <= limite_chars:
            return reconstruido
        itens.pop()
    return cabecalho


def _truncar_bloco_patch_completo(raw: str, candidatos: str, limite_chars: int) -> str:
    """Prioriza candidatos estruturados; corta evidencias brutas VI-VIII antes."""
    sep = "\n\n"
    raw = raw.strip()
    candidatos = candidatos.strip()

    if not raw and not candidatos:
        return ""
    if not candidatos:
        return _truncar_bloco_vi_viii(raw, limite_chars) if raw else ""

    if len(candidatos) >= limite_chars:
        return _truncar_bloco_candidatos(candidatos, limite_chars)

    cand_reservado = candidatos
    raw_limite = limite_chars - len(cand_reservado) - (len(sep) if raw else 0)
    raw_trunc = _truncar_bloco_vi_viii(raw, raw_limite) if raw and raw_limite > 0 else ""

    if raw_trunc:
        bloco = f"{raw_trunc}{sep}{cand_reservado}"
    else:
        bloco = cand_reservado

    if len(bloco) <= limite_chars:
        return bloco.strip()

    cand_limite = max(len(MARCADOR_CANDIDATOS_VII_VIII), limite_chars - len(raw_trunc) - len(sep))
    cand_trunc = _truncar_bloco_candidatos(cand_reservado, cand_limite)
    if raw_trunc:
        return f"{raw_trunc}{sep}{cand_trunc}".strip()
    return cand_trunc


def _anexar_evidencias_patch(
    texto_resumido: str,
    evidencias: str,
    limite_chars: int = LIMITE_CHARS_PROMPT_FINAL,
) -> str:
    """Anexa bloco de evidencias ao prompt de patch; prioriza candidatos estruturados."""
    if not evidencias or not evidencias.strip():
        return texto_resumido

    raw, candidatos = _separar_evidencias_e_candidatos(evidencias.strip())
    sep = "\n\n"
    bloco = raw
    if candidatos:
        bloco = f"{raw}{sep}{candidatos}".strip() if raw else candidatos

    combinado = f"{texto_resumido}{sep}{bloco}"
    if len(combinado) <= limite_chars:
        return combinado

    bloco_limite = limite_chars
    bloco = _truncar_bloco_patch_completo(raw, candidatos, bloco_limite)
    reserva = len(bloco) + len(sep)
    if reserva >= limite_chars:
        return bloco
    cabeca_max = limite_chars - reserva
    return f"{texto_resumido[:cabeca_max].rstrip()}{sep}{bloco}"


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
    texto_resumido = await _preparar_texto_para_llm(textos)

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


async def _preparar_texto_para_llm(textos: str) -> str:
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
    return texto_resumido


async def gerar_patch_llm(
    dados_deterministicos: dict,
    textos: str,
    validacao: dict,
) -> dict:
    """Gera patch LLM v2; falha nao bloqueante retorna patch vazio."""
    try:
        texto_resumido = await _preparar_texto_para_llm(textos)
    except RuntimeError as exc:
        logger.warning("Patch LLM: falha ao preparar texto (%s)", exc)
        return {"patch": [], "nao_encontrado": ["llm_indisponivel"]}

    evidencias_vi_viii = extrair_evidencias_acabamentos_equipamentos(textos)
    candidatos = extrair_candidatos_acabamentos_estruturados(textos)
    bloco_patch = evidencias_vi_viii
    if candidatos:
        bloco_patch = f"{evidencias_vi_viii}\n\n{candidatos}".strip()
    texto_resumido = _anexar_evidencias_patch(texto_resumido, bloco_patch)

    avisos = validacao.get("avisos_semanticos", [])
    avisos_txt = "\n".join(f"- {a}" for a in avisos) if avisos else "(nenhum)"

    prompt = (
        PROMPT_ENRIQUECER_PATCH.replace(
            "{json_deterministico}",
            json.dumps(dados_deterministicos, ensure_ascii=False, indent=2),
        )
        .replace("{campos_editaveis}", "\n".join(f"- {p}" for p in campos_llm_editaveis()))
        .replace("{avisos_semanticos}", avisos_txt)
        .replace("{textos}", texto_resumido)
    )

    logger.info("Enviando prompt de patch LLM v2...")
    try:
        resposta = await chamar_llm(prompt)
    except Exception as exc:
        logger.warning("Patch LLM: falha ao chamar LLM (%s)", exc)
        return {"patch": [], "nao_encontrado": ["llm_indisponivel"]}

    if not resposta:
        logger.warning("Patch LLM: resposta vazia")
        return {"patch": [], "nao_encontrado": ["llm_indisponivel"]}

    try:
        parsed = parsear_json(resposta)
    except json.JSONDecodeError as exc:
        logger.warning("Patch LLM: JSON invalido (%s)", exc)
        os.makedirs(PASTA_SAIDA, exist_ok=True)
        with open(caminho_saida(ARQ_RESPOSTA_BRUTA), "w", encoding="utf-8") as f:
            f.write(resposta)
        return {"patch": [], "nao_encontrado": ["llm_indisponivel"]}

    patch = parsed.get("patch", [])
    nao_encontrado = parsed.get("nao_encontrado", [])
    if not isinstance(patch, list):
        patch = []
    if not isinstance(nao_encontrado, list):
        nao_encontrado = []
    return {"patch": patch, "nao_encontrado": nao_encontrado}


def tratar_erro_llm(e: RuntimeError) -> None:
    logger.error("%s", e)
    if "LLM nao disponivel" in str(e):
        logger.error("Instale: pip install anthropic openai claude-agent-sdk")
        logger.error("Ou configure Claude CLI: npm install -g @anthropic-ai/claude-code")
