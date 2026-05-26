"""Matriz de responsabilidade por campo do JSON/planilha NBR 12721."""

from __future__ import annotations

from typing import Any, TypedDict

ORIGEM_DETERMINISTICA = "deterministico"
ORIGEM_CALCULO = "calculo"
ORIGEM_FORMULA_EXCEL = "formula_excel"
ORIGEM_LLM = "llm"
ORIGEM_REVISAO_MANUAL = "revisao_manual"

_ORIGENS_VALIDAS: frozenset[str] = frozenset(
    {
        ORIGEM_DETERMINISTICA,
        ORIGEM_CALCULO,
        ORIGEM_FORMULA_EXCEL,
        ORIGEM_LLM,
        ORIGEM_REVISAO_MANUAL,
    }
)


class CampoResponsabilidade(TypedDict):
    path: str
    origem: str
    llm_pode_alterar: bool
    status: str
    risco: str
    descricao: str


def _campo(
    path: str,
    origem: str,
    llm_pode_alterar: bool,
    status: str,
    risco: str,
    descricao: str,
) -> CampoResponsabilidade:
    return {
        "path": path,
        "origem": origem,
        "llm_pode_alterar": llm_pode_alterar,
        "status": status,
        "risco": risco,
        "descricao": descricao,
    }


CAMPOS_RESPONSABILIDADE: tuple[CampoResponsabilidade, ...] = (
    _campo(
        "incorporador.nome",
        ORIGEM_DETERMINISTICA,
        True,
        "implementado",
        "medio",
        "Razao social; LLM pode sugerir apenas se vazio ou lixo OCR.",
    ),
    _campo(
        "incorporador.cnpj",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "CNPJ extraido por regex/OCR; nao sobrescrever com inferencia LLM.",
    ),
    _campo(
        "incorporador.endereco",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "medio",
        "Endereco da incorporadora; exige evidencia documental objetiva.",
    ),
    _campo(
        "responsavel.nome",
        ORIGEM_DETERMINISTICA,
        True,
        "implementado",
        "medio",
        "Nome do responsavel tecnico; LLM pode sugerir apenas se vazio ou lixo OCR.",
    ),
    _campo(
        "responsavel.crea",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Registro CREA com padrao objetivo; nao alterar por LLM.",
    ),
    _campo(
        "responsavel.art",
        ORIGEM_REVISAO_MANUAL,
        False,
        "planejado",
        "alto",
        "ART raramente aparece de forma confiavel no OCR; revisao manual.",
    ),
    _campo(
        "responsavel.endereco",
        ORIGEM_DETERMINISTICA,
        True,
        "implementado",
        "medio",
        "Endereco do responsavel; LLM pode sugerir apenas se vazio ou lixo OCR.",
    ),
    _campo(
        "projeto.nomeEdificio",
        ORIGEM_DETERMINISTICA,
        True,
        "implementado",
        "medio",
        "Denominacao do empreendimento; LLM pode sugerir apenas se vazio ou lixo OCR.",
    ),
    _campo(
        "projeto.localConstrucao",
        ORIGEM_DETERMINISTICA,
        True,
        "implementado",
        "alto",
        "Local da obra; LLM pode sugerir apenas se vazio ou lixo OCR.",
    ),
    _campo(
        "projeto.cidadeUf",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Municipio/UF com padrao objetivo (ex.: Curitiba-PR).",
    ),
    _campo(
        "projeto.qtdUnidades",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Quantidade total de unidades (areas x quantidade de tipos).",
    ),
    _campo(
        "projeto.numPavimentos",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Numero de pavimentos do edificio.",
    ),
    _campo(
        "projeto.vagasUA",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "medio",
        "Vagas por unidade autonoma.",
    ),
    _campo(
        "projeto.vagasAcessorio",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "medio",
        "Vagas acessorias/duplas.",
    ),
    _campo(
        "projeto.vagasComum",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "medio",
        "Vagas comuns de garagem.",
    ),
    _campo(
        "projeto.areaTerreno",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Area do terreno em m2.",
    ),
    _campo(
        "projeto.dataAprovacao",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Data de aprovacao do projeto.",
    ),
    _campo(
        "projeto.numAlvara",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Numero do alvara de construcao.",
    ),
    _campo(
        "projeto.padraoAcabamento",
        ORIGEM_REVISAO_MANUAL,
        False,
        "planejado",
        "alto",
        "Padrao de acabamento; impacto tecnico e custo — revisao de engenharia.",
    ),
    _campo(
        "projeto.projetoPadrao.R",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao residencial (R) na planilha.",
    ),
    _campo(
        "projeto.projetoPadrao.CS",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao comercial/servicos (CS).",
    ),
    _campo(
        "projeto.projetoPadrao.CL",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao comercial leve (CL).",
    ),
    _campo(
        "projeto.projetoPadrao.CG",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao comercial geral (CG).",
    ),
    _campo(
        "projeto.projetoPadrao.CP",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao comercial pesado (CP).",
    ),
    _campo(
        "projeto.projetoPadrao.CP1Q",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Marcacao de padrao comercial pesado 1Q (CP1Q).",
    ),
    _campo(
        "quadro1.pavimentos",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Lista de pavimentos e areas do Quadro I.",
    ),
    _campo(
        "quadro2.unidades",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Lista de unidades e areas do Quadro II.",
    ),
    _campo(
        "quadro3.valorCub",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Valor CUB (SINDUSCON + regra por pavimentos); nao inferir por LLM.",
    ),
    _campo(
        "quadro3.sindicato",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Sindicato/fonte do CUB (preenchido com dados SINDUSCON).",
    ),
    _campo(
        "quadro3.mesCub",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "alto",
        "Mes/ano de referencia do CUB (preenchido com dados SINDUSCON).",
    ),
    _campo(
        "quadro3.projetoPadrao.*",
        ORIGEM_DETERMINISTICA,
        False,
        "parcial",
        "alto",
        "Linha de projeto-padrao do Quadro III (designacao, padrao, areaEquiv, etc.).",
    ),
    _campo(
        "quadro3.percentuais_e_adicionais",
        ORIGEM_FORMULA_EXCEL,
        False,
        "parcial",
        "alto",
        "Percentuais materiais/mao de obra, adicionais 6.3-6.6 e rateios; "
        "preferir formulas da planilha quando existirem.",
    ),
    _campo(
        "quadro4a.unidadesSubrogadas",
        ORIGEM_REVISAO_MANUAL,
        False,
        "planejado",
        "alto",
        "Unidades subrogadas exigem conferencia documental e engenharia.",
    ),
    _campo(
        "quadro5.garagens",
        ORIGEM_CALCULO,
        False,
        "implementado",
        "medio",
        "Texto derivado de projeto.vagasComum e projeto.vagasAcessorio.",
    ),
    _campo(
        "quadro5.*",
        ORIGEM_DETERMINISTICA,
        False,
        "implementado",
        "medio",
        "Campos descritivos do Quadro V (tipo, pavimentos, numeracao, etc.).",
    ),
    _campo(
        "quadro6.equipamentos",
        ORIGEM_LLM,
        True,
        "implementado",
        "medio",
        "Equipamentos e instalacoes do Quadro VI; enriquecimento por LLM.",
    ),
    _campo(
        "quadro7.acabamentos",
        ORIGEM_LLM,
        True,
        "implementado",
        "medio",
        "Acabamentos internos do Quadro VII; enriquecimento por LLM.",
    ),
    _campo(
        "quadro8.acabamentos",
        ORIGEM_LLM,
        True,
        "implementado",
        "medio",
        "Acabamentos de areas comuns do Quadro VIII; enriquecimento por LLM.",
    ),
)

# Folhas do schema cobertas por entradas agregadas (nao por path exato/wildcard).
PATHS_AGREGADOS: dict[str, frozenset[str]] = {
    "quadro3.percentuais_e_adicionais": frozenset(
        {
            "quadro3.percMateriais",
            "quadro3.percMaoObra",
            "quadro3.fundacoes",
            "quadro3.elevadores",
            "quadro3.fogoes",
            "quadro3.aquecedores",
            "quadro3.bombasRecalque",
            "quadro3.incineracao",
            "quadro3.arCondicionado",
            "quadro3.calefacao",
            "quadro3.ventilacao",
            "quadro3.outros6_3",
            "quadro3.playground",
            "quadro3.urbanizacao",
            "quadro3.recreacao",
            "quadro3.ajardinamento",
            "quadro3.instCondominio",
            "quadro3.outros6_5",
            "quadro3.outros6_6",
            "quadro3.impostos",
            "quadro3.projArq",
            "quadro3.projEstrut",
            "quadro3.projInst",
            "quadro3.projEsp",
            "quadro3.percConstrutor",
            "quadro3.percIncorporador",
        }
    ),
}

__all__ = [
    "CAMPOS_RESPONSABILIDADE",
    "ORIGEM_CALCULO",
    "ORIGEM_DETERMINISTICA",
    "ORIGEM_FORMULA_EXCEL",
    "ORIGEM_LLM",
    "ORIGEM_REVISAO_MANUAL",
    "PATHS_AGREGADOS",
    "campos_llm_editaveis",
    "campos_por_origem",
    "llm_pode_alterar",
    "origem_do_campo",
    "path_coberto_pela_matriz",
]

_indice_exato: dict[str, bool] | None = None
_indice_wildcards: list[tuple[str, bool]] | None = None


def _construir_indices() -> None:
    global _indice_exato, _indice_wildcards
    if _indice_exato is not None:
        return

    exato: dict[str, bool] = {}
    wildcards: list[tuple[str, bool]] = []
    for entrada in CAMPOS_RESPONSABILIDADE:
        path = entrada["path"]
        flag = entrada["llm_pode_alterar"]
        if path.endswith(".*"):
            prefixo = path[:-1]
            wildcards.append((prefixo, flag))
        else:
            exato[path] = flag

    wildcards.sort(key=lambda item: len(item[0]), reverse=True)
    _indice_exato = exato
    _indice_wildcards = wildcards


def llm_pode_alterar(path: str) -> bool:
    """Retorna se a LLM pode alterar o campo (match exato ou wildcard .*)."""
    _construir_indices()
    assert _indice_exato is not None
    assert _indice_wildcards is not None

    if path in _indice_exato:
        return _indice_exato[path]

    for prefixo, flag in _indice_wildcards:
        if path.startswith(prefixo):
            return flag

    return False


def campos_por_origem(origem: str) -> list[dict[str, Any]]:
    """Lista entradas da matriz filtradas por origem."""
    if origem not in _ORIGENS_VALIDAS:
        raise ValueError(f"Origem desconhecida: {origem!r}")
    return [dict(entrada) for entrada in CAMPOS_RESPONSABILIDADE if entrada["origem"] == origem]


def campos_llm_editaveis() -> list[str]:
    """Paths explicitamente marcados com llm_pode_alterar=True."""
    return sorted(
        entrada["path"]
        for entrada in CAMPOS_RESPONSABILIDADE
        if entrada["llm_pode_alterar"]
    )


def _entrada_exata(path: str) -> CampoResponsabilidade | None:
    for entrada in CAMPOS_RESPONSABILIDADE:
        if entrada["path"] == path:
            return entrada
    return None


def _entrada_wildcard(path: str) -> CampoResponsabilidade | None:
    candidatos: list[tuple[int, CampoResponsabilidade]] = []
    for entrada in CAMPOS_RESPONSABILIDADE:
        pattern = entrada["path"]
        if not pattern.endswith(".*"):
            continue
        prefixo = pattern[:-1]
        if path.startswith(prefixo):
            candidatos.append((len(prefixo), entrada))
    if not candidatos:
        return None
    candidatos.sort(key=lambda item: item[0], reverse=True)
    return candidatos[0][1]


def _entrada_agregado(path: str) -> CampoResponsabilidade | None:
    for agregado, membros in PATHS_AGREGADOS.items():
        if path in membros:
            return _entrada_exata(agregado)
    return None


def path_coberto_pela_matriz(path: str) -> bool:
    """True se o path tem entrada exata, wildcard ou agregado formal na matriz."""
    if _entrada_exata(path) is not None:
        return True
    if _entrada_agregado(path) is not None:
        return True
    return _entrada_wildcard(path) is not None


def origem_do_campo(path: str) -> str | None:
    """Retorna a origem documentada do path, ou None se nao coberto."""
    entrada = _entrada_exata(path) or _entrada_agregado(path) or _entrada_wildcard(path)
    return entrada["origem"] if entrada else None
