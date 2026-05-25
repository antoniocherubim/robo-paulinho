"""Validacao de completude do JSON extraido (NBR 12721)."""

from __future__ import annotations

__all__ = ["validar_dados_extraidos"]

CRITICOS: frozenset[str] = frozenset(
    {
        "incorporador.cnpj",
        "projeto.cidadeUf",
        "projeto.localConstrucao",
        "projeto.projetoPadrao.R",
        "projeto.qtdUnidades",
        "projeto.numPavimentos",
        "projeto.areaTerreno",
        "projeto.numAlvara",
        "quadro1.pavimentos",
        "quadro2.unidades",
    }
)

AVISOS: frozenset[str] = frozenset(
    {
        "incorporador.nome",
        "responsavel.nome",
        "responsavel.crea",
        "projeto.nomeEdificio",
        "projeto.vagasComum",
        "projeto.vagasAcessorio",
        "quadro3.valorCub",
        "quadro5.tipoEdificacao",
        "quadro5.garagens",
    }
)


def _get_path(dados: dict, path: str):
    atual = dados
    for parte in path.split("."):
        if not isinstance(atual, dict):
            return None
        if parte not in atual:
            return None
        atual = atual[parte]
    return atual


def _valor_preenchido(valor) -> bool:
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, bool):
        return valor is True
    if isinstance(valor, (int, float)):
        return valor != 0
    if isinstance(valor, list):
        return len(valor) > 0
    return bool(valor)


def _quadro1_preenchido(dados: dict) -> bool:
    pavs = _get_path(dados, "quadro1.pavimentos")
    if not isinstance(pavs, list) or len(pavs) == 0:
        return False
    if len(pavs) == 1:
        pav = pavs[0]
        if not isinstance(pav, dict):
            return False
        if not pav.get("nome", ""):
            return False
    return True


def _quadro2_preenchido(dados: dict) -> bool:
    unidades = _get_path(dados, "quadro2.unidades")
    if not isinstance(unidades, list) or len(unidades) == 0:
        return False
    if len(unidades) == 1:
        u = unidades[0]
        if not isinstance(u, dict):
            return False
        if not u.get("designacao", "") and u.get("areaPrivCobPadrao", 0) == 0:
            return False
    return True


def _campo_preenchido(dados: dict, path: str) -> bool:
    if path == "quadro1.pavimentos":
        return _quadro1_preenchido(dados)
    if path == "quadro2.unidades":
        return _quadro2_preenchido(dados)
    return _valor_preenchido(_get_path(dados, path))


def validar_dados_extraidos(dados: dict) -> dict:
    """Valida completude do JSON; nao altera dados nem chama LLM."""
    criticos_faltantes = [
        path for path in sorted(CRITICOS) if not _campo_preenchido(dados, path)
    ]
    avisos = [path for path in sorted(AVISOS) if not _campo_preenchido(dados, path)]
    total = len(CRITICOS) + len(AVISOS)
    preenchidos = total - len(criticos_faltantes) - len(avisos)
    score = round(preenchidos / total, 4) if total else 0.0
    return {
        "ok": len(criticos_faltantes) == 0,
        "score": score,
        "criticos_faltantes": criticos_faltantes,
        "avisos": avisos,
    }
