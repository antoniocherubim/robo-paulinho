"""Comparacao determinístico vs LLM no mesmo texto filtrado (sem re-OCR)."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
from typing import Any

from ..extraction.deterministic_extraction import extrair_dados_deterministico
from ..extraction.llm_patch import aplicar_patch_llm
from ..outputs.excel_tables import (
    CAMPOS_ACABAMENTO,
    CAMPOS_EQUIPAMENTO,
    linha_vazia,
)
from ..settings.config import (
    ARQ_COMPARACAO_MODOS_JSON,
    ARQ_DADOS_DETERMINISTICO_JSON,
    ARQ_DADOS_HIBRIDO_JSON,
    ARQ_DADOS_LLM_JSON,
    ARQ_PATCH_LLM_JSON,
    ARQ_TEXTO_FILTRADO,
    ARQ_VALIDACAO_DETERMINISTICO_JSON,
    ARQ_VALIDACAO_HIBRIDO_JSON,
    ARQ_VALIDACAO_LLM_JSON,
    caminho_comparacao,
    caminho_saida,
)
from .pipeline_llm import extrair_dados_via_llm, gerar_patch_llm
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

_PATHS_ESTRUTURAIS: tuple[str, ...] = (
    "projeto.qtdUnidades",
    "quadro1.pavimentos",
    "quadro2.unidades",
    "quadro3.valorCub",
    "quadro3.sindicato",
    "quadro3.mesCub",
    "quadro5.garagens",
    "incorporador.cnpj",
    "responsavel.crea",
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


def _valor_estrutural_preenchido(dados: dict, path: str) -> bool:
    valor = _obter_valor_path(dados, path)
    if path == "quadro1.pavimentos":
        if not isinstance(valor, list) or not valor:
            return False
        return any(
            isinstance(item, dict)
            and (
                str(item.get("nome", "")).strip()
                or item.get("qtdPavimentos", 0) not in (0, None, "")
                or item.get("areaPrivCobPadrao", 0) not in (0, None, "")
            )
            for item in valor
        )
    if path == "quadro2.unidades":
        if not isinstance(valor, list) or not valor:
            return False
        return any(
            isinstance(item, dict)
            and (
                str(item.get("designacao", "")).strip()
                or item.get("qtdUnidades", 0) not in (0, None, "")
                or item.get("areaPrivCobPadrao", 0) not in (0, None, "")
            )
            for item in valor
        )
    return _campo_textual_preenchido(dados, path)


def _perdas_estruturais(dados_det: dict, dados_out: dict) -> set[str]:
    perdidos: set[str] = set()
    for path in _PATHS_ESTRUTURAIS:
        if _valor_estrutural_preenchido(dados_det, path) and not _valor_estrutural_preenchido(
            dados_out, path
        ):
            perdidos.add(path)
    return perdidos


def _comparar_modo_vs_det(
    dados_det: dict,
    dados_out: dict,
    val_det: dict,
    val_out: dict,
    *,
    proteger_estrutura: bool = False,
) -> dict:
    campos_diferentes: list[dict] = []
    melhorias: set[str] = set()
    regressoes: set[str] = set()

    for path in CAMPOS_COMPARACAO:
        v_det = _obter_valor_path(dados_det, path)
        v_out = _obter_valor_path(dados_out, path)
        if not _valores_iguais(v_det, v_out):
            campos_diferentes.append(
                {
                    "path": path,
                    "deterministico": v_det,
                    "comparado": v_out,
                }
            )

    perdas = _perdas_estruturais(dados_det, dados_out) if proteger_estrutura else set()
    for path in perdas:
        regressoes.add(f"estrutural.perda:{path}")

    crit_det = set(val_det.get("criticos_faltantes", []))
    crit_out = set(val_out.get("criticos_faltantes", []))
    for item in crit_out - crit_det:
        regressoes.add(item)
    for item in crit_det - crit_out:
        if not proteger_estrutura or item not in perdas:
            melhorias.add(item)

    avis_det = set(val_det.get("avisos_semanticos", []))
    avis_out = set(val_out.get("avisos_semanticos", []))
    for aviso in avis_out - avis_det:
        regressoes.add(aviso)
    for aviso in avis_det - avis_out:
        if proteger_estrutura and perdas:
            continue
        if aviso.endswith(_LIXO_OCR_SUFFIX):
            campo_base = aviso[: -len(_LIXO_OCR_SUFFIX)]
            if _campo_textual_preenchido(dados_out, campo_base):
                melhorias.add(aviso)
            continue
        if aviso.endswith(".template_vazio"):
            path_quadro = aviso[: -len(".template_vazio")]
            if _lista_com_conteudo(dados_out, path_quadro, _campos_quadro(path_quadro)):
                melhorias.add(aviso)
            continue
        if not proteger_estrutura or not perdas:
            melhorias.add(aviso)

    for path, campos in _QUADROS_TEMPLATE_PATHS:
        if _lista_template_vazia(dados_det, path, campos) and _lista_com_conteudo(
            dados_out, path, campos
        ):
            if not (proteger_estrutura and perdas):
                melhorias.add(path)
        if _lista_com_conteudo(dados_det, path, campos) and _lista_template_vazia(
            dados_out, path, campos
        ):
            regressoes.add(path)

    if not proteger_estrutura:
        for aviso in avis_det - avis_out:
            if not aviso.endswith(_LIXO_OCR_SUFFIX):
                continue
            campo_base = aviso[: -len(_LIXO_OCR_SUFFIX)]
            if _campo_textual_preenchido(dados_out, campo_base):
                melhorias.add(aviso)

        for aviso in avis_out - avis_det:
            if not aviso.endswith(_LIXO_OCR_SUFFIX):
                continue
            campo_base = aviso[: -len(_LIXO_OCR_SUFFIX)]
            if _campo_textual_preenchido(dados_det, campo_base):
                regressoes.add(aviso)

    if val_out.get("ok") and not val_det.get("ok"):
        if not (proteger_estrutura and (perdas or crit_out - crit_det)):
            melhorias.add("validacao.ok")
    elif val_det.get("ok") and not val_out.get("ok"):
        regressoes.add("validacao.ok")

    if val_out.get("score", 0) > val_det.get("score", 0) + 0.01:
        if not (proteger_estrutura and (perdas or crit_out - crit_det)):
            melhorias.add("validacao.score")
    elif val_det.get("score", 0) > val_out.get("score", 0) + 0.01:
        regressoes.add("validacao.score")

    return {
        "melhorias": sorted(melhorias),
        "regressoes": sorted(regressoes),
        "campos_diferentes": campos_diferentes,
        "perdas_estruturais": sorted(perdas),
    }


def _campos_quadro(path_quadro: str) -> tuple[str, ...]:
    for path, campos in _QUADROS_TEMPLATE_PATHS:
        if path == path_quadro:
            return campos
    return ()


def gerar_relatorio_comparacao(
    dados_det: dict,
    dados_llm: dict,
    val_det: dict,
    val_llm: dict,
    *,
    dados_hibrido: dict | None = None,
    val_hibrido: dict | None = None,
    patch_llm: dict | None = None,
) -> dict:
    comp_llm = _comparar_modo_vs_det(dados_det, dados_llm, val_det, val_llm)
    relatorio: dict[str, Any] = {
        "deterministico": _resumo_validacao(val_det),
        "llm": _resumo_validacao(val_llm),
        "melhorias_llm": comp_llm["melhorias"],
        "regressoes_llm": comp_llm["regressoes"],
        "campos_diferentes": comp_llm["campos_diferentes"],
    }

    if dados_hibrido is not None and val_hibrido is not None:
        comp_hib = _comparar_modo_vs_det(
            dados_det,
            dados_hibrido,
            val_det,
            val_hibrido,
            proteger_estrutura=True,
        )
        relatorio["hibrido"] = {
            **_resumo_validacao(val_hibrido),
            "melhorias": comp_hib["melhorias"],
            "regressoes": comp_hib["regressoes"],
            "campos_diferentes": comp_hib["campos_diferentes"],
            "perdas_estruturais": comp_hib["perdas_estruturais"],
            "patch_aplicado": len(dados_hibrido.get("_patch_llm_aplicado", [])),
            "patch_rejeitado": len(dados_hibrido.get("_patch_llm_rejeitado", [])),
        }
        if patch_llm is not None:
            relatorio["hibrido"]["nao_encontrado"] = list(
                patch_llm.get("nao_encontrado", [])
            )

    return relatorio


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

    logger.info("Comparacao: patch LLM v2 (hibrido)...")
    patch_result = await gerar_patch_llm(dados_det, textos, val_det)
    path_patch = caminho_comparacao(ARQ_PATCH_LLM_JSON)
    _salvar_json(patch_result, path_patch)

    dados_hibrido = aplicar_patch_llm(copy.deepcopy(dados_det), patch_result.get("patch", []))
    path_dados_hib = caminho_comparacao(ARQ_DADOS_HIBRIDO_JSON)
    path_val_hib = caminho_comparacao(ARQ_VALIDACAO_HIBRIDO_JSON)
    val_hibrido = _processar_modo_comparacao(
        dados_hibrido, cub_info, path_dados_hib, path_val_hib
    )
    logger.info("Hibrido salvo: %s", path_dados_hib)

    logger.info("Comparacao: extracao LLM legado...")
    dados_llm = await extrair_dados_via_llm(textos, cub_info)
    path_dados_llm = caminho_comparacao(ARQ_DADOS_LLM_JSON)
    path_val_llm = caminho_comparacao(ARQ_VALIDACAO_LLM_JSON)
    val_llm = _processar_modo_comparacao(
        dados_llm, cub_info, path_dados_llm, path_val_llm
    )
    logger.info("LLM legado salvo: %s", path_dados_llm)

    relatorio = gerar_relatorio_comparacao(
        dados_det,
        dados_llm,
        val_det,
        val_llm,
        dados_hibrido=dados_hibrido,
        val_hibrido=val_hibrido,
        patch_llm=patch_result,
    )
    path_relatorio = caminho_comparacao(ARQ_COMPARACAO_MODOS_JSON)
    _salvar_json(relatorio, path_relatorio)

    logger.info("=" * 50)
    logger.info("COMPARACAO DETERMINISTICO vs LLM")
    logger.info("=" * 50)
    logger.info("Relatorio: %s", path_relatorio)
    logger.info(
        "Deterministico: ok=%s score=%.4f | Hibrido: ok=%s score=%.4f | LLM: ok=%s score=%.4f",
        val_det.get("ok"),
        val_det.get("score", 0),
        val_hibrido.get("ok"),
        val_hibrido.get("score", 0),
        val_llm.get("ok"),
        val_llm.get("score", 0),
    )
    if relatorio.get("hibrido", {}).get("melhorias"):
        logger.info(
            "Melhorias hibrido (%s):",
            len(relatorio["hibrido"]["melhorias"]),
        )
        for item in relatorio["hibrido"]["melhorias"]:
            logger.info("  + %s", item)
    if relatorio.get("hibrido", {}).get("regressoes"):
        logger.warning(
            "Regressoes hibrido (%s):",
            len(relatorio["hibrido"]["regressoes"]),
        )
        for item in relatorio["hibrido"]["regressoes"]:
            logger.warning("  - %s", item)
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
