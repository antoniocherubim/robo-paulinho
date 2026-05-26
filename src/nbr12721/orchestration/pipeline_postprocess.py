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
    "validar_cub_semantico",
]

_TOLERANCIA_VALOR_CUB = 0.01


def _tipo_cub_residencial_por_pavimentos(num_pavimentos: int, valores: dict) -> str:
    """Regra pragmatica: >=8 pav. prefere R16-N, depois R8-N, R1-N, R4-N."""
    if num_pavimentos <= 0:
        return ""
    if num_pavimentos >= 8:
        ordem = ("R16-N", "R8-N", "R1-N", "R4-N")
    else:
        ordem = ("R1-N", "R4-N", "R8-N", "R16-N")
    for tipo in ordem:
        if tipo in valores:
            return tipo
    return ""


def preencher_cub_automatico(dados: dict, cub_info: dict | None) -> None:
    if not cub_info or not cub_info.get("valores"):
        logger.info("CUB automatico nao preenchido: informacoes CUB indisponiveis")
        return
    q3 = dados.setdefault("quadro3", {})
    if q3.get("valorCub"):
        logger.info("CUB automatico nao sobrescrito: valorCub ja preenchido (%s)", q3.get("valorCub"))
        return
    pp = dados.get("projeto", {}).get("projetoPadrao", {})
    pp3 = q3.get("projetoPadrao", {})
    valores = cub_info["valores"]
    candidatos: list[str] = []
    padrao_q3 = str(pp3.get("padrao", "")).strip().upper()
    if padrao_q3:
        candidatos.append(padrao_q3)
    if pp.get("CS"):
        candidatos.append("CSL-8")
    if pp.get("R"):
        try:
            num_pav = int(dados.get("projeto", {}).get("numPavimentos") or 0)
        except (TypeError, ValueError):
            num_pav = 0
        if num_pav <= 0:
            logger.warning(
                "CUB residencial nao preenchido: numPavimentos ausente ou zero "
                "(regra por pavimentos exige dado conhecido)"
            )
        else:
            tipo_res = _tipo_cub_residencial_por_pavimentos(num_pav, valores)
            if tipo_res:
                candidatos.append(tipo_res)
            if num_pav < 8:
                candidatos.extend(["R1-N", "R4-N"])
    tipo = next((t for t in candidatos if t and t in valores), "")
    if not tipo:
        logger.warning(
            "CUB automatico nao preenchido: nenhum tipo compativel encontrado | candidatos=%s | disponiveis=%s",
            [t for t in candidatos if t],
            sorted(valores.keys()),
        )
        return
    q3["valorCub"] = valores[tipo]
    q3["sindicato"] = cub_info["sindicato"]
    q3["mesCub"] = cub_info["mesAno"]
    num_pav_log = dados.get("projeto", {}).get("numPavimentos", 0)
    logger.info(
        "CUB residencial selecionado por numPavimentos: tipo=%s numPavimentos=%s valor=R$ %s (%s)",
        tipo,
        num_pav_log,
        formatar_brl(q3["valorCub"]),
        cub_info["mesAno"],
    )


def preencher_derivados_seguros(dados: dict) -> None:
    """Completa campos derivados sem inventar dados externos ao JSON."""
    logger.debug("Preenchendo campos derivados seguros")
    _preencher_garagens_quadro5(dados)


def _preencher_garagens_quadro5(dados: dict) -> None:
    q5 = dados.get("quadro5")
    projeto = dados.get("projeto")
    if not isinstance(q5, dict) or not isinstance(projeto, dict):
        logger.debug("Garagens nao derivadas: quadro5/projeto ausente ou invalido")
        return
    if q5.get("garagens"):
        logger.debug("Garagens nao derivadas: quadro5.garagens ja preenchido")
        return

    partes: list[str] = []
    vagas_comuns = _inteiro_positivo(projeto.get("vagasComum"))
    vagas_duplas = _inteiro_positivo(projeto.get("vagasAcessorio"))
    if vagas_comuns > 0:
        partes.append(f"{vagas_comuns} vagas comuns")
    if vagas_duplas > 0:
        partes.append(f"{vagas_duplas} vagas duplas")
    q5["garagens"] = "; ".join(partes)
    if q5["garagens"]:
        logger.info("Garagens derivadas para quadro5: %s", q5["garagens"])


def _tipo_cub_pelo_valor(valor_cub: float, valores: dict) -> str:
    for tipo, val in valores.items():
        try:
            if abs(float(val) - float(valor_cub)) <= _TOLERANCIA_VALOR_CUB:
                return str(tipo)
        except (TypeError, ValueError):
            continue
    return ""


def validar_cub_semantico(dados: dict, cub_info: dict | None) -> list[str]:
    """Avisos quando CUB residencial alto nao esta disponivel na fonte parseada."""
    if not cub_info or not isinstance(cub_info.get("valores"), dict):
        return []
    valores = cub_info["valores"]
    if not valores:
        return []

    try:
        num_pav = int(dados.get("projeto", {}).get("numPavimentos") or 0)
    except (TypeError, ValueError):
        num_pav = 0
    try:
        valor_cub = float(dados.get("quadro3", {}).get("valorCub") or 0)
    except (TypeError, ValueError):
        valor_cub = 0.0
    if num_pav < 8 or valor_cub <= 0:
        return []

    pp = dados.get("projeto", {}).get("projetoPadrao", {})
    if not isinstance(pp, dict) or not pp.get("R"):
        return []

    tem_r16 = "R16-N" in valores
    tem_r8 = "R8-N" in valores
    avisos: list[str] = []

    if not tem_r16 and not tem_r8:
        avisos.append("quadro3.valorCub.tipo_residencial_alto_indisponivel")
        tipo_usado = _tipo_cub_pelo_valor(valor_cub, valores)
        if tipo_usado in ("R1-N", "R4-N"):
            avisos.append("quadro3.valorCub.fallback_baixo_para_predio_alto")

    return avisos


def _inteiro_positivo(valor) -> int:
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return numero if numero > 0 else 0


def registrar_validacao_dados(dados: dict, cub_info: dict | None = None) -> dict:
    preencher_derivados_seguros(dados)
    resultado = validar_dados_extraidos(dados)
    extras = validar_cub_semantico(dados, cub_info)
    resultado["avisos_semanticos"] = sorted(
        set(resultado.get("avisos_semanticos", []) + extras)
    )

    os.makedirs(PASTA_SAIDA, exist_ok=True)
    with open(caminho_saida(ARQ_VALIDACAO_JSON), "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    logger.info("Relatorio de validacao salvo: %s", caminho_saida(ARQ_VALIDACAO_JSON))

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

    if resultado.get("avisos_semanticos"):
        logger.warning("Avisos semanticos:")
        for item in resultado["avisos_semanticos"]:
            logger.warning("  - %s", item)

    return resultado
