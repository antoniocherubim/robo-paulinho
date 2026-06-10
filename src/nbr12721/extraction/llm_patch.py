"""Patch LLM controlado sobre JSON deterministico (ABNT NBR 12721)."""

from __future__ import annotations

import copy
import re
from typing import Any

from ..outputs.excel_tables import (
    CAMPOS_ACABAMENTO,
    CAMPOS_EQUIPAMENTO,
    linha_vazia,
)
from .field_responsibility import llm_pode_alterar

__all__ = [
    "aplicar_patch_llm",
    "filtrar_patch_permitido",
    "validar_item_patch",
]

_CONFIANCAS_VALIDAS = frozenset({"baixa", "media", "alta"})
_PATHS_LISTA: dict[str, tuple[str, ...]] = {
    "quadro6.equipamentos": CAMPOS_EQUIPAMENTO,
    "quadro7.acabamentos": CAMPOS_ACABAMENTO,
    "quadro8.acabamentos": CAMPOS_ACABAMENTO,
}
_PATHS_TEXTUAIS = frozenset(
    {
        "incorporador.nome",
        "responsavel.nome",
        "responsavel.endereco",
        "projeto.nomeEdificio",
        "projeto.localConstrucao",
    }
)
_RE_MARCADOR_PDF = re.compile(r"\[[^\]]+\.pdf\]", re.IGNORECASE)
_RE_FICARA_CONDIC = re.compile(r"FICARA\s+CONDIC", re.IGNORECASE)


def _obter_valor_path(dados: dict, path: str) -> Any:
    atual: Any = dados
    for parte in path.split("."):
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte)
    return atual


def _definir_valor_path(dados: dict, path: str, valor: Any) -> None:
    partes = path.split(".")
    atual = dados
    for parte in partes[:-1]:
        if not isinstance(atual.get(parte), dict):
            atual[parte] = {}
        atual = atual[parte]
    atual[partes[-1]] = valor


def _texto_substituivel(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return True
        if texto.startswith(","):
            return True
        if _RE_MARCADOR_PDF.search(texto):
            return True
        if _RE_FICARA_CONDIC.search(texto):
            return True
        return False
    return False


def _lista_com_conteudo_real(valor: Any, campos: tuple[str, ...]) -> bool:
    if not isinstance(valor, list) or not valor:
        return False
    return any(
        isinstance(item, dict) and not linha_vazia(item, campos) for item in valor
    )


def validar_item_patch(item: dict) -> tuple[bool, str]:
    if not isinstance(item, dict):
        return False, "item deve ser dict"

    path = item.get("path")
    if not isinstance(path, str) or not path.strip():
        return False, "path invalido"

    if "valor" not in item:
        return False, "valor ausente"

    evidencia = item.get("evidencia")
    if not isinstance(evidencia, str) or not evidencia.strip():
        return False, "evidencia ausente ou vazia"

    confianca = item.get("confianca")
    if confianca not in _CONFIANCAS_VALIDAS:
        return False, "confianca invalida"

    if not llm_pode_alterar(path):
        return False, "path nao permitido pela matriz"

    valor = item["valor"]
    if path in _PATHS_LISTA:
        if not _lista_com_conteudo_real(valor, _PATHS_LISTA[path]):
            return False, "lista vazia ou template sem conteudo"

    return True, ""


def filtrar_patch_permitido(patch: list[dict]) -> tuple[list[dict], list[dict]]:
    permitidos: list[dict] = []
    rejeitados: list[dict] = []
    for item in patch:
        if not isinstance(item, dict):
            rejeitados.append({"item": item, "motivo": "item deve ser dict"})
            continue
        ok, motivo = validar_item_patch(item)
        if ok:
            permitidos.append(item)
        else:
            rejeitados.append(
                {
                    "path": item.get("path", ""),
                    "motivo": motivo,
                    "item": item,
                }
            )
    return permitidos, rejeitados


def aplicar_patch_llm(dados: dict, patch: list[dict]) -> dict:
    """Aplica patch permitido sobre copia profunda; nao muta o dict original."""
    resultado = copy.deepcopy(dados)
    permitidos, rejeitados_validacao = filtrar_patch_permitido(patch)
    aplicados: list[dict] = []
    rejeitados: list[dict] = list(rejeitados_validacao)

    for item in permitidos:
        path = item["path"]
        valor = item["valor"]

        if path in _PATHS_TEXTUAIS:
            atual = _obter_valor_path(resultado, path)
            if not _texto_substituivel(atual):
                rejeitados.append(
                    {
                        "path": path,
                        "motivo": "campo textual ja preenchido e sem lixo OCR",
                    }
                )
                continue

        _definir_valor_path(resultado, path, copy.deepcopy(valor))
        aplicados.append(
            {
                "path": path,
                "evidencia": item["evidencia"],
                "confianca": item["confianca"],
            }
        )

    if aplicados:
        resultado["_patch_llm_aplicado"] = aplicados
    if rejeitados:
        resultado["_patch_llm_rejeitado"] = rejeitados

    return resultado
