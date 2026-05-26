"""Mapeamento de campos JSON para celulas do template ABNT NBR 12721:2006."""

from __future__ import annotations

from typing import Any

INFO_PRELIMINARES_CELLS: dict[str, str] = {
    "incorporador.nome": "F5",
    "incorporador.cnpj": "F6",
    "incorporador.endereco": "F7",
    "responsavel.nome": "G10",
    "responsavel.crea": "G11",
    "responsavel.art": "G12",
    "responsavel.endereco": "G13",
    "projeto.nomeEdificio": "G16",
    "projeto.localConstrucao": "G17",
    "projeto.cidadeUf": "G18",
    "projeto.projetoPadrao.R": "H19",
    "projeto.projetoPadrao.CS": "J19",
    "projeto.projetoPadrao.CL": "L19",
    "projeto.projetoPadrao.CG": "H20",
    "projeto.projetoPadrao.CP": "J20",
    "projeto.projetoPadrao.CP1Q": "L20",
    "projeto.qtdUnidades": "G21",
    "projeto.padraoAcabamento": "G22",
    "projeto.numPavimentos": "G23",
    "projeto.vagasUA": "I25",
    "projeto.vagasAcessorio": "I26",
    "projeto.vagasComum": "I27",
    "projeto.areaTerreno": "H28",
    "projeto.dataAprovacao": "H29",
    "projeto.numAlvara": "H30",
}

QUADRO1_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO I",
    "local_header": "D5",
    "start_row": 17,
    "max_rows": 25,
    "columns": {
        "nome": 2,
        "areaPrivCobPadrao": 3,
        "areaPrivCobDifReal": 4,
        "areaPrivCobDifEquiv": 5,
        "areaComumNPCobPadrao": 8,
        "areaComumNPCobDifReal": 9,
        "areaComumNPCobDifEquiv": 10,
        "areaComumPCobPadrao": 13,
        "areaComumPCobDifReal": 14,
        "areaComumPCobDifEquiv": 15,
        "qtdPavimentos": 20,
    },
}

QUADRO2_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO II",
    "start_row": 17,
    "max_rows": 25,
    "columns": {
        "designacao": 2,
        "areaPrivCobPadrao": 3,
        "areaPrivCobDifReal": 4,
        "areaPrivCobDifEquiv": 5,
        "areaComumNPCobPadrao": 8,
        "areaComumNPCobDifReal": 9,
        "areaComumNPCobDifEquiv": 10,
        "qtdUnidades": 22,
    },
}

QUADRO6_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO VI",
    "start_row": 12,
    "max_rows": 30,
    "columns": {
        "nome": 2,
        "tipo": 4,
        "acabamento": 6,
        "detalhes": 8,
    },
}

QUADRO7_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO VII",
    "start_row": 12,
    "max_rows": 30,
    "columns": {
        "dependencia": 2,
        "pisos": 4,
        "paredes": 7,
        "tetos": 10,
        "outros": 12,
    },
}

QUADRO8_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO VIII",
    "start_row": 12,
    "max_rows": 30,
    "columns": {
        "dependencia": 2,
        "pisos": 4,
        "paredes": 7,
        "tetos": 10,
        "outros": 12,
    },
}

QUADRO5_CELLS: dict[str, str] = {
    "tipoEdificacao": "F11",
    "numPavimentos": "F13",
    "unidadesPorPav": "F15",
    "numeracao": "F17",
    "pilotis": "F19",
    "transicao": "F21",
    "garagens": "F23",
    "pavComunitarios": "F24",
    "outrosPav": "F25",
    "dataAprovacao": "F26",
    "outrasIndicacoes": "F28",
}

QUADRO3_CELLS: dict[str, str] = {
    "projetoPadrao.designacao": "C18",
    "projetoPadrao.padrao": "D18",
    "projetoPadrao.numPav": "E18",
    "projetoPadrao.areaEquiv": "F18",
    "projetoPadrao.quartos": "G18",
    "projetoPadrao.salas": "H18",
    "projetoPadrao.banheiros": "I18",
    "projetoPadrao.quartosEmp": "K18",
    "sindicato": "G19",
    "mesCub": "G20",
    "valorCub": "L20",
}

QUADRO3_PERCENTUAIS: tuple[tuple[str, str], ...] = (
    ("L34", "fundacoes"),
    ("L35", "elevadores"),
    ("L37", "fogoes"),
    ("L38", "aquecedores"),
    ("L39", "bombasRecalque"),
    ("L40", "incineracao"),
    ("L41", "arCondicionado"),
    ("L42", "calefacao"),
    ("L43", "ventilacao"),
    ("L44", "outros6_3"),
    ("L45", "playground"),
    ("L47", "urbanizacao"),
    ("L48", "recreacao"),
    ("L49", "ajardinamento"),
    ("L50", "instCondominio"),
    ("L51", "outros6_5"),
    ("L52", "outros6_6"),
    ("L54", "impostos"),
    ("L56", "projArq"),
    ("L57", "projEstrut"),
    ("L58", "projInst"),
    ("L59", "projEsp"),
)

QUADRO4B_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO IV B",
    "start_row": 14,
    "max_rows": 25,
    "columns": {
        "outrasAreasPriv": 4,
        "qtdUnidades": 9,
    },
}

QUADRO4B1_CONFIG: dict[str, Any] = {
    "sheet": "QUADRO IV B.1",
    "start_row": 15,
    "max_rows": 25,
    "columns": {
        "outrasAreasPriv": 4,
        "areaTerrExcl": 8,
        "areaTerrComum": 9,
    },
}


def resolver_celula(ws, ref: str, valor) -> None:
    """Escreve em celula fixa; ignora erro de celula mesclada."""
    try:
        ws[ref] = valor
    except AttributeError:
        pass


def obter_valor_path(dados: dict, path: str):
    atual: Any = dados
    for parte in path.split("."):
        if not isinstance(atual, dict):
            return None
        atual = atual.get(parte)
    return atual
