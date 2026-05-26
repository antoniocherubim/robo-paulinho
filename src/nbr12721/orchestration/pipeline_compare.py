"""Comparacao determinístico vs LLM no mesmo texto filtrado (sem re-OCR)."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from ..extraction.deterministic_extraction import extrair_dados_deterministico
from ..outputs.excel_tables import (
    CAMPOS_ACABAMENTO,
    CAMPOS_EQUIPAMENTO,
    linha_vazia,
)
from ..settings.config import (
    ARQ_COMPARACAO_MODOS_JSON,
    ARQ_DADOS_DETERMINISTICO_JSON,
    ARQ_DADOS_LLM_JSON,
    ARQ_TEXTO_FILTRADO,
    ARQ_VALIDACAO_DETERMINISTICO_JSON,
    ARQ_VALIDACAO_LLM_JSON,
    caminho_comparacao,
    caminho_saida,
)
from .pipeline_llm import extrair_dados_via_llm
from .pipeline_postprocess import montar_resultado_validacao, preencher_cub_automatico

logger = logging.getLogger(__name__)

__all__ = [
    "carregar_texto_filtrado_cache",
    "executar_comparacao_modos",
    "gerar_relatorio_comparacao",
]

CAMPOS_COMPARACAO: tuple[str, ...] = (
    "incorporador.nome",
    "incorporador.cnpj",
    "responsavel.nome",
    "responsavel.crea",
    "responsavel.endereco",
    "projeto.nomeEdificio",
    "projeto.localConstrucao",
    "projeto.cidadeUf",
    "projeto.qtdUnidades",
    "projeto.numPavimentos",
    "projeto.areaTerreno",
    "projeto.numAlvara",
    "quadro1.pavimentos",
    "quadro2.unidades",
    "quadro3.valorCub",
    "quadro5.garagens",
    "quadro6.equipamentos",
    "quadro7.acabamentos",
    "quadro8.acabamentos",
)

_QUADROS_TEMPLATE_PATHS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("quadro6.equipamentos", CAMPOS_EQUIPAMENTO),
    ("quadro7.acabamentos", CAMPOS_ACABAMENTO),
    ("quadro8.acabamentos", CAMPOS_ACABAMENTO),
)

_LIXO_OCR_SUFFIX = ".lixo_ocr"


def carregar_texto_filtrado_cache() -> str:
    """Le textos_filtrados.txt sem refiltrar e sem OCR."""
    path = caminho_saida(ARQ_TEXTO_FILTRADO)
    if not os.path.isfile(path):
        logger.error(
            "Cache de texto filtrado nao encontrado: %s\n"
            "Execute o pipeline com OCR antes (gera textos_filtrados.txt).",
            path,
        )
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        textos = f.read()
    if not textos.strip():
        logger.error("Cache de texto filtrado vazio: %s", path)
        sys.exit(1)
    logger.info("Usando texto filtrado em cache: %s (%s chars)", path, len(textos))
    return textos


def _obter_valor_path(dados: dict, path: str) -> Any:
    atual: Any = dados
    for parte in path.split("."):
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte)
    return atual


def _normalizar_valor_comparacao(valor: Any) -> str:
    if valor is None:
        return ""
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False, sort_keys=True, default=str)
    if isinstance(valor, float):
        return f"{valor:.6f}".rstrip("0").rstrip(".")
    if isinstance(valor, bool):
        return "true" if valor else "false"
    return str(valor).strip()


def _valores_iguais(a: Any, b: Any) -> bool:
    return _normalizar_valor_comparacao(a) == _normalizar_valor_comparacao(b)


def _resumo_validacao(resultado: dict) -> dict:
    return {
        "ok": resultado.get("ok", False),
        "score": resultado.get("score", 0),
        "criticos_faltantes": list(resultado.get("criticos_faltantes", [])),
        "avisos_semanticos": list(resultado.get("avisos_semanticos", [])),
    }


def _lista_template_vazia(dados: dict, path: str, campos: tuple[str, ...]) -> bool:
    itens = _obter_valor_path(dados, path)
    if not isinstance(itens, list) or not itens:
        return True
    return all(
        isinstance(item, dict) and linha_vazia(item, campos) for item in itens
    )


def _lista_com_conteudo(dados: dict, path: str, campos: tuple[str, ...]) -> bool:
    itens = _obter_valor_path(dados, path)
    if not isinstance(itens, list):
        return False
    return any(
        isinstance(item, dict) and not linha_vazia(item, campos) for item in itens
    )


def _campo_textual_preenchido(dados: dict, path: str) -> bool:
    valor = _obter_valor_path(dados, path)
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, (int, float)):
        return valor != 0
    return bool(valor)


def gerar_relatorio_comparacao(
    dados_det: dict,
    dados_llm: dict,
    val_det: dict,
    val_llm: dict,
) -> dict:
    campos_diferentes: list[dict] = []
    melhorias: set[str] = set()
    regressoes: set[str] = set()

    for path in CAMPOS_COMPARACAO:
        v_det = _obter_valor_path(dados_det, path)
        v_llm = _obter_valor_path(dados_llm, path)
        if not _valores_iguais(v_det, v_llm):
            campos_diferentes.append(
                {
                    "path": path,
                    "deterministico": v_det,
                    "llm": v_llm,
                }
            )

    crit_det = set(val_det.get("criticos_faltantes", []))
    crit_llm = set(val_llm.get("criticos_faltantes", []))
    for item in crit_det - crit_llm:
        melhorias.add(item)
    for item in crit_llm - crit_det:
        regressoes.add(item)

    avis_det = set(val_det.get("avisos_semanticos", []))
    avis_llm = set(val_llm.get("avisos_semanticos", []))
    for item in avis_det - avis_llm:
        melhorias.add(item)
    for item in avis_llm - avis_det:
        regressoes.add(item)

    for path, campos in _QUADROS_TEMPLATE_PATHS:
        if _lista_template_vazia(dados_det, path, campos) and _lista_com_conteudo(
            dados_llm, path, campos
        ):
            melhorias.add(path)
        if _lista_com_conteudo(dados_det, path, campos) and _lista_template_vazia(
            dados_llm, path, campos
        ):
            regressoes.add(path)

    for aviso in avis_det - avis_llm:
        if not aviso.endswith(_LIXO_OCR_SUFFIX):
            continue
        campo_base = aviso[: -len(_LIXO_OCR_SUFFIX)]
        if _campo_textual_preenchido(dados_llm, campo_base):
            melhorias.add(aviso)

    for aviso in avis_llm - avis_det:
        if not aviso.endswith(_LIXO_OCR_SUFFIX):
            continue
        campo_base = aviso[: -len(_LIXO_OCR_SUFFIX)]
        if _campo_textual_preenchido(dados_det, campo_base):
            regressoes.add(aviso)

    if val_llm.get("ok") and not val_det.get("ok"):
        melhorias.add("validacao.ok")
    elif val_det.get("ok") and not val_llm.get("ok"):
        regressoes.add("validacao.ok")

    if val_llm.get("score", 0) > val_det.get("score", 0) + 0.01:
        melhorias.add("validacao.score")
    elif val_det.get("score", 0) > val_llm.get("score", 0) + 0.01:
        regressoes.add("validacao.score")

    return {
        "deterministico": _resumo_validacao(val_det),
        "llm": _resumo_validacao(val_llm),
        "melhorias_llm": sorted(melhorias),
        "regressoes_llm": sorted(regressoes),
        "campos_diferentes": campos_diferentes,
    }


def _salvar_json(dados: dict, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def _processar_modo_comparacao(
    dados: dict,
    cub_info: dict | None,
    path_dados: str,
    path_validacao: str,
) -> dict:
    """CUB → derivados/validacao → salva dados e validacao alinhados."""
    preencher_cub_automatico(dados, cub_info)
    resultado = montar_resultado_validacao(dados, cub_info)
    _salvar_json(dados, path_dados)
    _salvar_json(resultado, path_validacao)
    return resultado


async def executar_comparacao_modos(textos: str, cub_info: dict | None) -> dict:
    """Executa ambos os modos no mesmo texto; salva apenas em saida/comparacao/."""
    os.makedirs(caminho_comparacao("."), exist_ok=True)

    logger.info("Comparacao: extracao deterministica...")
    dados_det = extrair_dados_deterministico(textos)
    path_dados_det = caminho_comparacao(ARQ_DADOS_DETERMINISTICO_JSON)
    path_val_det = caminho_comparacao(ARQ_VALIDACAO_DETERMINISTICO_JSON)
    val_det = _processar_modo_comparacao(
        dados_det, cub_info, path_dados_det, path_val_det
    )
    logger.info("Deterministico salvo: %s", path_dados_det)

    logger.info("Comparacao: extracao LLM...")
    dados_llm = await extrair_dados_via_llm(textos, cub_info)
    path_dados_llm = caminho_comparacao(ARQ_DADOS_LLM_JSON)
    path_val_llm = caminho_comparacao(ARQ_VALIDACAO_LLM_JSON)
    val_llm = _processar_modo_comparacao(
        dados_llm, cub_info, path_dados_llm, path_val_llm
    )
    logger.info("LLM salvo: %s", path_dados_llm)

    relatorio = gerar_relatorio_comparacao(dados_det, dados_llm, val_det, val_llm)
    path_relatorio = caminho_comparacao(ARQ_COMPARACAO_MODOS_JSON)
    _salvar_json(relatorio, path_relatorio)

    logger.info("=" * 50)
    logger.info("COMPARACAO DETERMINISTICO vs LLM")
    logger.info("=" * 50)
    logger.info("Relatorio: %s", path_relatorio)
    logger.info(
        "Deterministico: ok=%s score=%.4f | LLM: ok=%s score=%.4f",
        val_det.get("ok"),
        val_det.get("score", 0),
        val_llm.get("ok"),
        val_llm.get("score", 0),
    )
    if relatorio["melhorias_llm"]:
        logger.info("Melhorias LLM (%s):", len(relatorio["melhorias_llm"]))
        for item in relatorio["melhorias_llm"]:
            logger.info("  + %s", item)
    if relatorio["regressoes_llm"]:
        logger.warning("Regressoes LLM (%s):", len(relatorio["regressoes_llm"]))
        for item in relatorio["regressoes_llm"]:
            logger.warning("  - %s", item)
    if relatorio["campos_diferentes"]:
        logger.info(
            "Campos com valores diferentes: %s",
            len(relatorio["campos_diferentes"]),
        )

    return relatorio
