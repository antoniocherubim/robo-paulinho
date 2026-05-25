"""Computo de campos faltantes do extrator deterministico."""

from __future__ import annotations

import re

from .base_fields import _texto_menciona_crea
from .patterns import (
    RE_BLOCO_ADMINISTRATIVO,
    RE_EMPRESA_JURIDICA,
    RE_MENCAO_ROTULO_INCORPORADOR,
    linha_contem_cnpj,
)
from .floors import (
    _quadro1_apenas_template,
    _texto_menciona_pavimentos_ou_areas,
)
from .units import (
    _quadro2_apenas_template,
    _texto_menciona_aptos,
    _texto_menciona_vagas_comuns,
    _texto_menciona_vagas_duplas,
)


def _texto_menciona_incorporador(texto: str) -> bool:
    if RE_MENCAO_ROTULO_INCORPORADOR.search(texto):
        return True
    linhas = texto.splitlines()
    for i, linha in enumerate(linhas):
        if not linha_contem_cnpj(linha):
            continue
        for j in range(max(0, i - 2), min(len(linhas), i + 3)):
            candidata = linhas[j]
            if RE_BLOCO_ADMINISTRATIVO.search(candidata):
                continue
            if RE_EMPRESA_JURIDICA.search(candidata):
                return True
    return False


def _texto_menciona_local_obra(texto: str) -> bool:
    return bool(
        re.search(
            r"LOCAL\s+DA\s+OBRA|ENDE[RRE][CÇ]O\s+DA\s+OBRA|"
            r"SITUAD[OA]\s+NO",
            texto,
            re.IGNORECASE,
        )
    )


def _texto_menciona_nome_edificio(texto: str) -> bool:
    return bool(
        re.search(
            r"NOME\s+DO\s+EDIF[IÍ]CIO|EMPREENDIMENTO",
            texto,
            re.IGNORECASE,
        )
    )


def _computar_dados_faltantes(dados: dict, texto: str) -> list[str]:
    faltantes: list[str] = []
    inc = dados["incorporador"]
    proj = dados["projeto"]
    resp = dados["responsavel"]
    q3 = dados["quadro3"]["projetoPadrao"]

    if not inc.get("cnpj"):
        faltantes.append("incorporador.cnpj")
    if not proj.get("cidadeUf"):
        faltantes.append("projeto.cidadeUf")
    if not proj.get("dataAprovacao"):
        faltantes.append("projeto.dataAprovacao")
    if not proj.get("numAlvara"):
        faltantes.append("projeto.numAlvara")
    if not proj.get("areaTerreno"):
        faltantes.append("projeto.areaTerreno")
    if not proj.get("projetoPadrao", {}).get("R"):
        faltantes.append("projeto.projetoPadrao.R")
    if not q3.get("designacao"):
        faltantes.append("quadro3.projetoPadrao.designacao")
    if _texto_menciona_crea(texto) and not resp.get("crea"):
        faltantes.append("responsavel.crea")
    if not proj.get("qtdUnidades"):
        faltantes.append("projeto.qtdUnidades")
    if not proj.get("numPavimentos"):
        faltantes.append("projeto.numPavimentos")
    if not proj.get("vagasComum") and _texto_menciona_vagas_comuns(texto):
        faltantes.append("projeto.vagasComum")
    if not proj.get("vagasAcessorio") and _texto_menciona_vagas_duplas(texto):
        faltantes.append("projeto.vagasAcessorio")
    if _quadro2_apenas_template(dados["quadro2"]["unidades"]) and _texto_menciona_aptos(
        texto
    ):
        faltantes.append("quadro2.unidades")
    if _quadro1_apenas_template(
        dados["quadro1"]["pavimentos"]
    ) and _texto_menciona_pavimentos_ou_areas(texto):
        faltantes.append("quadro1.pavimentos")
    if not inc.get("nome") and _texto_menciona_incorporador(texto):
        faltantes.append("incorporador.nome")
    if _texto_menciona_crea(texto) and not resp.get("nome"):
        faltantes.append("responsavel.nome")
    if not proj.get("localConstrucao") and _texto_menciona_local_obra(texto):
        faltantes.append("projeto.localConstrucao")
    if not proj.get("nomeEdificio") and _texto_menciona_nome_edificio(texto):
        faltantes.append("projeto.nomeEdificio")

    return faltantes
