"""Pos-processamento do pipeline: CUB e validacao do JSON."""
import json
import logging
import os

from ..extraction.validation import validar_dados_extraidos
from ..outputs.formatacao import formatar_brl
from ..settings.config import ARQ_VALIDACAO_JSON, PASTA_SAIDA, caminho_saida

logger = logging.getLogger(__name__)

__all__ = [
    "preencher_derivados_seguros",
    "preencher_cub_automatico",
    "registrar_validacao_dados",
]


def preencher_cub_automatico(dados: dict, cub_info: dict | None) -> None:
    if not cub_info or not cub_info.get("valores"):
        return
    q3 = dados.setdefault("quadro3", {})
    if q3.get("valorCub"):
        return
    pp = dados.get("projeto", {}).get("projetoPadrao", {})
    pp3 = q3.get("projetoPadrao", {})
    candidatos = [
        str(pp3.get("padrao", "")).strip().upper(),
        "CSL-8" if pp.get("CS") else "",
        "R4-N" if pp.get("R") else "",
        "R1-N" if pp.get("R") else "",
    ]
    tipo = next((t for t in candidatos if t and t in cub_info["valores"]), "")
    if not tipo:
        return
    q3["valorCub"] = cub_info["valores"][tipo]
    q3["sindicato"] = cub_info["sindicato"]
    q3["mesCub"] = cub_info["mesAno"]
    logger.info(
        "CUB preenchido automaticamente: %s = R$ %s (%s)",
        tipo,
        formatar_brl(q3["valorCub"]),
        cub_info["mesAno"],
    )


def preencher_derivados_seguros(dados: dict) -> None:
    """Completa campos derivados sem inventar dados externos ao JSON."""
    _preencher_garagens_quadro5(dados)


def _preencher_garagens_quadro5(dados: dict) -> None:
    q5 = dados.get("quadro5")
    projeto = dados.get("projeto")
    if not isinstance(q5, dict) or not isinstance(projeto, dict):
        return
    if q5.get("garagens"):
        return

    partes: list[str] = []
    vagas_comuns = _inteiro_positivo(projeto.get("vagasComum"))
    vagas_duplas = _inteiro_positivo(projeto.get("vagasAcessorio"))
    if vagas_comuns > 0:
        partes.append(f"{vagas_comuns} vagas comuns")
    if vagas_duplas > 0:
        partes.append(f"{vagas_duplas} vagas duplas")
    q5["garagens"] = "; ".join(partes)


def _inteiro_positivo(valor) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return numero if numero > 0 else 0


def registrar_validacao_dados(dados: dict) -> dict:
    preencher_derivados_seguros(dados)
    resultado = validar_dados_extraidos(dados)

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(caminho_saida(ARQ_VALIDACAO_JSON), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    logger.info(
        "Validacao JSON: ok=%s score=%.4f",
        resultado["ok"],
        resultado["score"],
    )

    if resultado["criticos_faltantes"]:
        logger.warning("Criticos faltantes:")
        for item in resultado["criticos_faltantes"]:
            logger.warning("  - %s", item)

    if resultado["avisos"]:
        logger.info("Avisos de validacao:")
        for item in resultado["avisos"]:
            logger.info("  - %s", item)

    return resultado
