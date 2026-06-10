"""Orquestrador do extrator deterministico NBR 12721."""

from __future__ import annotations

import logging
import time

from .base_fields import (
    _detectar_padrao_r,
    _extrair_area_terreno,
    _extrair_cidade_uf,
    _extrair_cnpj,
    _extrair_crea,
    _extrair_data_aprovacao,
    _extrair_designacao,
    _extrair_num_alvara,
    _normalizar_cnpj,
    _normalizar_crea,
)
from .floors import _extrair_pavimentos_quadro1
from .identity import (
    _extrair_incorporador_nome,
    _extrair_local_construcao,
    _extrair_nome_edificio,
    _extrair_responsavel_endereco,
    _extrair_responsavel_nome,
)
from .missing import _computar_dados_faltantes
from .quadro5 import _preencher_quadro5
from .quadro8 import _preencher_quadro8
from .schema import _esqueleto_vazio
from .units import (
    _extrair_num_pavimentos,
    _extrair_qtd_unidades,
    _extrair_unidades_quadro2,
    _extrair_vagas_comuns,
    _extrair_vagas_duplas,
)

logger = logging.getLogger(__name__)

__all__ = ["extrair_dados_deterministico"]


def _preencher_campos_base(dados: dict, texto: str) -> str:
    dados["incorporador"]["cnpj"] = _extrair_cnpj(texto)
    dados["projeto"]["cidadeUf"] = _extrair_cidade_uf(texto)
    dados["projeto"]["dataAprovacao"] = _extrair_data_aprovacao(texto)
    dados["projeto"]["numAlvara"] = _extrair_num_alvara(texto)
    dados["projeto"]["areaTerreno"] = _extrair_area_terreno(texto)
    dados["projeto"]["projetoPadrao"]["R"] = _detectar_padrao_r(texto)
    designacao = _extrair_designacao(texto)
    dados["quadro3"]["projetoPadrao"]["designacao"] = designacao
    return designacao


def _preencher_unidades_pavimentos_vagas(dados: dict, texto: str) -> None:
    dados["quadro2"]["unidades"] = _extrair_unidades_quadro2(texto)
    dados["projeto"]["qtdUnidades"] = _extrair_qtd_unidades(texto)
    dados["projeto"]["numPavimentos"] = _extrair_num_pavimentos(texto)
    dados["projeto"]["vagasComum"] = _extrair_vagas_comuns(texto)
    dados["projeto"]["vagasAcessorio"] = _extrair_vagas_duplas(texto)
    dados["quadro1"]["pavimentos"] = _extrair_pavimentos_quadro1(texto)


def _preencher_identificacao(dados: dict, texto: str, designacao: str) -> None:
    dados["projeto"]["localConstrucao"] = _extrair_local_construcao(texto)
    dados["responsavel"]["crea"] = _extrair_crea(texto)
    dados["responsavel"]["nome"] = _extrair_responsavel_nome(
        texto,
        dados["responsavel"]["crea"],
    )
    dados["responsavel"]["endereco"] = _extrair_responsavel_endereco(texto)
    dados["incorporador"]["nome"] = _extrair_incorporador_nome(texto)
    dados["projeto"]["nomeEdificio"] = _extrair_nome_edificio(texto, designacao)


def extrair_dados_deterministico(texto: str) -> dict:
    """Extrai campos do texto e retorna dict no schema de dados_extraidos.json."""
    inicio = time.monotonic()
    logger.info("Extrator deterministico iniciado | texto=%s chars", len(texto or ""))
    dados = _esqueleto_vazio()

    designacao = _preencher_campos_base(dados, texto)
    logger.info(
        "Campos base: cnpj=%s | cidadeUf=%s | alvara=%s | areaTerreno=%s | residencial=%s",
        bool(dados["incorporador"]["cnpj"]),
        dados["projeto"]["cidadeUf"] or "-",
        dados["projeto"]["numAlvara"] or "-",
        dados["projeto"]["areaTerreno"],
        dados["projeto"]["projetoPadrao"]["R"],
    )

    _preencher_unidades_pavimentos_vagas(dados, texto)
    logger.info(
        "Unidades/pavimentos/vagas: qtdUnidades=%s | numPavimentos=%s | quadro1=%s | quadro2=%s | vagasComum=%s | vagasDuplas=%s",
        dados["projeto"]["qtdUnidades"],
        dados["projeto"]["numPavimentos"],
        len(dados["quadro1"]["pavimentos"]),
        len(dados["quadro2"]["unidades"]),
        dados["projeto"]["vagasComum"],
        dados["projeto"]["vagasAcessorio"],
    )

    _preencher_identificacao(dados, texto, designacao)
    logger.info(
        "Identificacao: incorporador=%s | responsavel=%s | crea=%s | local=%s | edificio=%s",
        dados["incorporador"]["nome"] or "-",
        dados["responsavel"]["nome"] or "-",
        dados["responsavel"]["crea"] or "-",
        dados["projeto"]["localConstrucao"] or "-",
        dados["projeto"]["nomeEdificio"] or "-",
    )

    _preencher_quadro5(dados, texto)
    _preencher_quadro8(dados, texto)
    n_acabamentos = sum(
        1
        for item in dados["quadro8"]["acabamentos"]
        if isinstance(item, dict) and str(item.get("dependencia", "")).strip()
    )
    logger.info("Quadro VIII: acabamentos=%s", n_acabamentos)
    dados["_dados_faltantes"] = _computar_dados_faltantes(dados, texto)
    logger.info(
        "Extrator deterministico finalizado | faltantes=%s | %.2fs",
        len(dados["_dados_faltantes"]),
        time.monotonic() - inicio,
    )

    return dados
