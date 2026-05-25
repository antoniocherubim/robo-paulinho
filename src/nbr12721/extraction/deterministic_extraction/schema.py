"""Schema canonico vazio produzido pelo extrator deterministico."""

from __future__ import annotations


def _esqueleto_vazio() -> dict:
    """Retorna dict novo com o schema completo e defaults do PROMPT_EXTRAIR."""
    return {
        "incorporador": {"nome": "", "cnpj": "", "endereco": ""},
        "responsavel": {"nome": "", "crea": "", "art": "", "endereco": ""},
        "projeto": {
            "nomeEdificio": "",
            "localConstrucao": "",
            "cidadeUf": "",
            "projetoPadrao": {
                "R": False,
                "CS": False,
                "CL": False,
                "CG": False,
                "CP": False,
                "CP1Q": False,
            },
            "qtdUnidades": 0,
            "padraoAcabamento": "",
            "numPavimentos": 0,
            "vagasUA": 0,
            "vagasAcessorio": 0,
            "vagasComum": 0,
            "areaTerreno": 0,
            "dataAprovacao": "",
            "numAlvara": "",
        },
        "quadro1": {
            "pavimentos": [
                {
                    "nome": "",
                    "areaPrivCobPadrao": 0,
                    "areaPrivCobDifReal": 0,
                    "areaPrivCobDifEquiv": 0,
                    "areaComumNPCobPadrao": 0,
                    "areaComumNPCobDifReal": 0,
                    "areaComumNPCobDifEquiv": 0,
                    "areaComumPCobPadrao": 0,
                    "areaComumPCobDifReal": 0,
                    "areaComumPCobDifEquiv": 0,
                    "qtdPavimentos": 1,
                }
            ],
        },
        "quadro2": {
            "unidades": [
                {
                    "designacao": "",
                    "areaPrivCobPadrao": 0,
                    "areaPrivCobDifReal": 0,
                    "areaPrivCobDifEquiv": 0,
                    "areaComumNPCobPadrao": 0,
                    "areaComumNPCobDifReal": 0,
                    "areaComumNPCobDifEquiv": 0,
                    "qtdUnidades": 1,
                    "outrasAreasPriv": 0,
                    "areaTerrExcl": 0,
                    "areaTerrComum": 0,
                }
            ],
        },
        "quadro3": {
            "projetoPadrao": {
                "designacao": "",
                "padrao": "",
                "numPav": "",
                "areaEquiv": "",
                "quartos": "",
                "salas": "",
                "banheiros": "",
                "quartosEmp": "",
            },
            "sindicato": "",
            "mesCub": "",
            "valorCub": 0,
            "percMateriais": 0,
            "percMaoObra": 0,
            "fundacoes": 0,
            "elevadores": 0,
            "fogoes": 0,
            "aquecedores": 0,
            "bombasRecalque": 0,
            "incineracao": 0,
            "arCondicionado": 0,
            "calefacao": 0,
            "ventilacao": 0,
            "outros6_3": 0,
            "playground": 0,
            "urbanizacao": 0,
            "recreacao": 0,
            "ajardinamento": 0,
            "instCondominio": 0,
            "outros6_5": 0,
            "outros6_6": 0,
            "impostos": 0,
            "projArq": 0,
            "projEstrut": 0,
            "projInst": 0,
            "projEsp": 0,
            "percConstrutor": 0,
            "percIncorporador": 0,
        },
        "quadro4a": {"unidadesSubrogadas": []},
        "quadro5": {
            "tipoEdificacao": "",
            "numPavimentos": "",
            "unidadesPorPav": "",
            "numeracao": "",
            "pilotis": "",
            "transicao": "",
            "garagens": "",
            "pavComunitarios": "",
            "outrosPav": "",
            "dataAprovacao": "",
            "outrasIndicacoes": "",
        },
        "quadro6": {
            "equipamentos": [
                {"nome": "", "tipo": "", "acabamento": "", "detalhes": ""}
            ],
        },
        "quadro7": {
            "acabamentos": [
                {
                    "dependencia": "",
                    "pisos": "",
                    "paredes": "",
                    "tetos": "",
                    "outros": "",
                }
            ],
        },
        "quadro8": {
            "acabamentos": [
                {
                    "dependencia": "",
                    "pisos": "",
                    "paredes": "",
                    "tetos": "",
                    "outros": "",
                }
            ],
        },
        "_dados_faltantes": [],
    }
