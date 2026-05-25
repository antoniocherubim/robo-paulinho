"""Extracao deterministica de dados NBR 12721 a partir de texto (sem LLM)."""

from __future__ import annotations

import re

__all__ = ["extrair_dados_deterministico"]

_RE_DATA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_RE_CIDADE_UF_LINHA = re.compile(
    r"(?<![A-Za-zÀ-ÿ])([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \t]{2,40}?)[ \t]*[-/][ \t]*([A-Z]{2})\b",
    re.IGNORECASE,
)
_RE_CONTEXTO_PROFISSIONAL = re.compile(
    r"\b(?:CREA|CAU|CNPJ)\b",
    re.IGNORECASE,
)
_JANELA_LINHAS_DATA_CONTEXTO = 2
_RE_ALVARA = re.compile(
    r"(?:N[°ºo.]?\s*DE\s+)?ALVAR[AÁ]\s*:?\s*([0-9]+(?:\s*/\s*[0-9]+)?)",
    re.IGNORECASE,
)
_RE_TERRENO = re.compile(
    r"TERRENO\s*:\s*([\d.,]+)\s*M",
    re.IGNORECASE,
)
_RE_DESIGNACAO = re.compile(
    r"(EDIFICA[CÇ][AÃ]O\s+RESIDENCIAL\s+MULTIFAMILIAR\s+VERTICAL\s*\[RMV\])",
    re.IGNORECASE,
)
_RE_CNPJ_DIGITOS = re.compile(r"\d")
_RE_CREA = re.compile(
    r"CREA\s*([A-Z]{2})\s*[-/]?\s*(\d{4,6})\s*[/]?\s*([A-Z])?",
    re.IGNORECASE,
)
_RE_CREA_COLADO = re.compile(
    r"CREA\s*([A-Z]{2})\s*[-]?\s*(\d{4,6})\s*([A-Z])?",
    re.IGNORECASE,
)
_PALAVRAS_DATA_CONTEXTO = re.compile(
    r"aprova[cç][aã]o|aprovacao|alvar[aá]|alvara|data\s+do\s+projeto",
    re.IGNORECASE,
)
_PALAVRAS_PADRAO_R = re.compile(
    r"residencial.*(?:multifamiliar|vertical|\[rmv\])|"
    r"(?:multifamiliar|vertical|\[rmv\]).*residencial",
    re.IGNORECASE,
)
_RE_AREA_X_APTOS = re.compile(
    r"(?P<area>[\d.,]+)\s*[xX×]\s*(?P<qtd>\d+)\s*(?:APTOS?|APARTAMENTOS?)\b",
    re.IGNORECASE,
)
_RE_QTD_APTOS = re.compile(
    r"(?<![\d.,])\b(?P<qtd>\d+)\s*(?:APTOS?|APARTAMENTOS?)(?!/\s*PAV)\b",
    re.IGNORECASE,
)
_RE_INTERVALO_PAV = re.compile(
    r"\b(\d+)\s*(?:º|°)?\s*AO\s*(\d+)\s*(?:º|°)?\b",
    re.IGNORECASE,
)
_RE_N_PAVIMENTOS = re.compile(r"\b(\d+)\s+PAVIMENTOS?\b", re.IGNORECASE)
_RE_TERREO = re.compile(
    r"PAVIMENTO\s+T[EÉ]RREO|\bT[EÉ]RREO\b",
    re.IGNORECASE,
)
_RE_COBERTURA = re.compile(r"\bCOBERTURA\b", re.IGNORECASE)
_RE_VAGAS_COMUNS = re.compile(
    r"TOTAL\s+DE\s+VAGAS\s+COMUNS?\s*:?\s*(\d+)",
    re.IGNORECASE,
)
_RE_VAGAS_DUPLAS = re.compile(
    r"TOTAL\s+DE\s+VAGAS\s+DUPLAS?\s*:?\s*(\d+)",
    re.IGNORECASE,
)
_RE_APTOS_POR_PAV = re.compile(
    r"\b(\d+)\s*APTOS?\s*/\s*PAV\b",
    re.IGNORECASE,
)
_RE_LOCAL_OBRA = re.compile(
    r"LOCAL\s+DA\s+OBRA\s*:?\s*(.+)",
    re.IGNORECASE,
)
_RE_ENDERECO_OBRA = re.compile(
    r"ENDE[RRE][CÇ]O\s+DA\s+OBRA\s*:?\s*(.+)",
    re.IGNORECASE,
)
_RE_SITUADO = re.compile(
    r"^SITUAD[OA]\s+NO\s+(.+)",
    re.IGNORECASE,
)
_RE_PROCESSO_APROVACAO = re.compile(
    r"Processo\s+Aprova[cç][aã]o\s+n[°ºo.]?\s*([\d./-]+)",
    re.IGNORECASE,
)
_RE_INCORPORADOR_ROTULO = re.compile(
    r"(?:INCORPORADOR|INCORPORADORA|CONSTRUTORA|PROPRIET[AÁ]RIO)\s*:?\s*(.+)",
    re.IGNORECASE,
)
_RE_PAGOTTO = re.compile(r"PAGOTTO\s*[_\-]\s*(.+)", re.IGNORECASE)
_RE_CORTE_MARCADOR_ADMIN = re.compile(
    r"\b(?:Processo|N[°ºo.]|ALVAR[AÁ]|CREA|CAU|CNPJ)\b",
    re.IGNORECASE,
)
_RE_NOME_EDIFICIO_ROTULO = re.compile(
    r"(?:NOME\s+DO\s+EDIF[IÍ]CIO|EMPREENDIMENTO)\s*:?\s*(.+)",
    re.IGNORECASE,
)
_RE_EDIFICIO_LINHA = re.compile(
    r"^EDIF[IÍ]CIO\s+(.+)",
    re.IGNORECASE,
)
_RE_PROFISSAO_SPLIT = re.compile(
    r"\b(?:ENGENHEIR[OA]|ARQUITET[OA]|CREA|CAU)\b",
    re.IGNORECASE,
)
_RE_PROFISSAO_NOME = re.compile(
    r"\b(?:ENGENHEIR[OA]|ARQUITET[OA])(?:\s+CIVIL|\s+URBANISTA)?\b",
    re.IGNORECASE,
)
_RE_NOME_RESP_INVALIDO = re.compile(
    r"\b(?:Processo|PAGOTTO|CNPJ|ALVAR[AÁ]|N[°ºo.])\b",
    re.IGNORECASE,
)
_RE_LOGRADOURO = re.compile(
    r"\b(?:rua|avenida|av\.|travessa|alameda)\b",
    re.IGNORECASE,
)
_RE_CEP = re.compile(r"\d{5}-?\d{3}")
_RE_TEL = re.compile(r"\[\d+\]")
_RE_EMAIL = re.compile(r"@")


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


def _parse_numero_br(valor: str) -> float:
    """Converte numero brasileiro (ex.: 8.958,97) para float."""
    limpo = valor.strip()
    if not limpo:
        return 0.0
    limpo = re.sub(r"\s+", "", limpo)
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    else:
        limpo = limpo.replace(",", "")
    try:
        return float(limpo)
    except ValueError:
        return 0.0


def _somente_digitos(texto: str) -> str:
    return "".join(_RE_CNPJ_DIGITOS.findall(texto))


def _normalizar_cnpj(raw: str) -> str:
    """Normaliza CNPJ com OCR ruim para XX.XXX.XXX/XXXX-XX."""
    digitos = _somente_digitos(raw)
    if len(digitos) != 14:
        return ""
    base = digitos[:8]
    ordem = digitos[8:12]
    dv = digitos[12:14]
    return f"{base[:2]}.{base[2:5]}.{base[5:8]}/{ordem}-{dv}"


def _extrair_cnpj(texto: str) -> str:
    padroes = [
        re.compile(
            r"CNPJ\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2})",
            re.IGNORECASE,
        ),
        re.compile(
            r"CNPJ\s*(\d{2}\.?\d{3}\.?\d{3}\d{4}-?\d{2})",
            re.IGNORECASE,
        ),
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\b"),
        re.compile(r"\b(\d{2}\.\d{3}\.\d{3}\d{4}-\d{2})\b"),
    ]
    for padrao in padroes:
        m = padrao.search(texto)
        if m:
            normalizado = _normalizar_cnpj(m.group(1))
            if normalizado:
                return normalizado
    blocos = re.findall(
        r"CNPJ\s*([\d./-]{14,20})",
        texto,
        flags=re.IGNORECASE,
    )
    for bloco in blocos:
        normalizado = _normalizar_cnpj(bloco)
        if normalizado:
            return normalizado
    return ""


def _capitalizar_cidade(cidade: str) -> str:
    partes = cidade.strip().split()
    return " ".join(p.capitalize() for p in partes if p)


def _normalizar_cidade_uf(cidade: str, uf: str) -> str:
    return f"{_capitalizar_cidade(cidade)}-{uf.upper()}"


def _linha_eh_contexto_profissional(linha: str) -> bool:
    return bool(_RE_CONTEXTO_PROFISSIONAL.search(linha))


def _extrair_cidade_uf(texto: str) -> str:
    for linha in texto.splitlines():
        if _linha_eh_contexto_profissional(linha):
            continue
        for m in _RE_CIDADE_UF_LINHA.finditer(linha):
            cidade = m.group(1).strip()
            uf = m.group(2).strip()
            if len(cidade) >= 3 and uf.isalpha():
                return _normalizar_cidade_uf(cidade, uf)
    return ""


def _data_valida(dia: str, mes: str, ano: str) -> bool:
    try:
        d, m, a = int(dia), int(mes), int(ano)
    except ValueError:
        return False
    return 1 <= d <= 31 and 1 <= m <= 12 and 1900 <= a <= 2100


def _formatar_data(dia: str, mes: str, ano: str) -> str:
    return f"{int(dia):02d}/{int(mes):02d}/{ano}"


def _indices_linhas_com_contexto_data(linhas: list[str]) -> list[int]:
    return [
        i
        for i, linha in enumerate(linhas)
        if _PALAVRAS_DATA_CONTEXTO.search(linha)
    ]


def _extrair_data_aprovacao(texto: str) -> str:
    linhas = texto.splitlines()
    candidatas_gerais: list[tuple[int, str]] = []
    melhor_contexto: tuple[int, int, str] | None = None

    anchors = _indices_linhas_com_contexto_data(linhas)

    for idx, linha in enumerate(linhas):
        for m in _RE_DATA.finditer(linha):
            if not _data_valida(m.group(1), m.group(2), m.group(3)):
                continue
            data_fmt = _formatar_data(m.group(1), m.group(2), m.group(3))
            candidatas_gerais.append((idx, data_fmt))

            if not anchors:
                continue

            for anchor in anchors:
                if abs(idx - anchor) > _JANELA_LINHAS_DATA_CONTEXTO:
                    continue
                depois_anchor = 0 if idx >= anchor else 1
                chave = (abs(idx - anchor), depois_anchor, idx)
                if melhor_contexto is None or chave < melhor_contexto[:3]:
                    melhor_contexto = (*chave, data_fmt)

    if melhor_contexto is not None:
        return melhor_contexto[3]
    if candidatas_gerais:
        return candidatas_gerais[0][1]
    return ""


def _extrair_num_alvara(texto: str) -> str:
    m = _RE_ALVARA.search(texto)
    if not m:
        return ""
    valor = re.sub(r"\s+", "", m.group(1))
    return valor.replace(" ", "")


def _extrair_area_terreno(texto: str) -> float:
    m = _RE_TERRENO.search(texto)
    if not m:
        return 0.0
    return _parse_numero_br(m.group(1))


def _detectar_padrao_r(texto: str) -> bool:
    return bool(_PALAVRAS_PADRAO_R.search(texto))


def _limpar_designacao(frase: str) -> str:
    return re.sub(r"\s+", " ", frase.strip())


def _extrair_designacao(texto: str) -> str:
    m = _RE_DESIGNACAO.search(texto)
    if m:
        return _limpar_designacao(m.group(1))
    for linha in texto.splitlines():
        if re.search(r"residencial", linha, re.IGNORECASE) and re.search(
            r"multifamiliar|vertical|\[rmv\]", linha, re.IGNORECASE
        ):
            trecho = re.search(
                r"(EDIFICA[CÇ][AÃ]O\s+.+?\[RMV\])",
                linha,
                re.IGNORECASE,
            )
            if trecho:
                return _limpar_designacao(trecho.group(1))
    return ""


def _normalizar_crea(raw: str) -> str:
    """Normaliza registro CREA com variantes OCR."""
    texto = raw.strip()
    if not texto:
        return ""

    m = _RE_CREA.search(texto)
    if m:
        uf = m.group(1).upper()
        numero = m.group(2)
        sufixo = (m.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    m_colado = _RE_CREA_COLADO.search(texto)
    if m_colado:
        uf = m_colado.group(1).upper()
        numero = m_colado.group(2)
        sufixo = (m_colado.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    compacto = re.sub(r"\s+", "", texto, flags=re.IGNORECASE)
    compacto = re.sub(r"^CREA", "", compacto, flags=re.IGNORECASE)
    m2 = re.match(r"^([A-Z]{2})-?(\d{4,6})([A-Z])?$", compacto, re.IGNORECASE)
    if m2:
        uf = m2.group(1).upper()
        numero = m2.group(2)
        sufixo = (m2.group(3) or "").upper()
        if sufixo:
            return f"{uf}-{numero}/{sufixo}"
        return f"{uf}-{numero}"

    return ""


def _extrair_crea(texto: str) -> str:
    if not re.search(r"CREA", texto, re.IGNORECASE):
        return ""
    for linha in texto.splitlines():
        if re.search(r"CREA", linha, re.IGNORECASE):
            normalizado = _normalizar_crea(linha)
            if normalizado:
                return normalizado
    return _normalizar_crea(texto)


def _texto_menciona_crea(texto: str) -> bool:
    return bool(re.search(r"CREA", texto, re.IGNORECASE))


def _normalizar_linha_ocr(linha: str) -> str:
    return re.sub(r"\s+", " ", linha.strip())


def _limpar_texto_campo(texto: str) -> str:
    return re.sub(r"\s+", " ", texto.strip())


def _eh_apenas_cidade_uf(texto: str) -> bool:
    limpo = _limpar_texto_campo(texto)
    return bool(
        re.fullmatch(
            r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \t]*[-/][A-Z]{2}",
            limpo,
            flags=re.IGNORECASE,
        )
    )


def _extrair_local_construcao(texto: str) -> str:
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        for padrao in (_RE_LOCAL_OBRA, _RE_ENDERECO_OBRA):
            m = padrao.search(linha_n)
            if m:
                valor = _limpar_texto_campo(m.group(1))
                if valor and not _eh_apenas_cidade_uf(valor):
                    return valor
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        m = _RE_SITUADO.match(linha_n)
        if m:
            valor = _limpar_texto_campo(m.group(1))
            if valor and not _eh_apenas_cidade_uf(valor):
                return valor
    return ""


def _nome_candidato_invalido(nome: str) -> bool:
    return bool(_RE_NOME_RESP_INVALIDO.search(nome))


def _nome_antes_profissao(linha: str, *, somente_engenheiro_arquiteto: bool = False) -> str:
    padrao = (
        _RE_PROFISSAO_NOME if somente_engenheiro_arquiteto else _RE_PROFISSAO_SPLIT
    )
    m = padrao.search(linha)
    if not m:
        return ""
    antes = _limpar_texto_campo(linha[: m.start()].strip(" -–—"))
    if not antes:
        return ""
    if _nome_candidato_invalido(antes):
        return ""
    palavras = [p for p in antes.split() if re.search(r"[A-Za-zÀ-ÿ]", p, re.IGNORECASE)]
    if len(palavras) < 2:
        return ""
    if re.fullmatch(
        r"(?:ENGENHEIR[OA]|ARQUITET[OA])(?:\s+CIVIL|\s+URBANISTA)?",
        antes,
        flags=re.IGNORECASE,
    ):
        return ""
    return antes


def _extrair_responsavel_nome(texto: str, crea: str = "") -> str:
    if _texto_menciona_crea(texto):
        for linha in texto.splitlines():
            if re.search(r"CREA", linha, re.IGNORECASE):
                nome = _nome_antes_profissao(
                    linha, somente_engenheiro_arquiteto=True
                )
                if nome:
                    return nome
        return ""
    for linha in texto.splitlines():
        if re.search(r"CAU", linha, re.IGNORECASE):
            nome = _nome_antes_profissao(linha)
            if nome:
                return nome
    return ""


def _extrair_responsavel_endereco(texto: str) -> str:
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        if not _RE_LOGRADOURO.search(linha_n):
            continue
        if (
            _RE_CEP.search(linha_n)
            or _RE_TEL.search(linha_n)
            or _RE_EMAIL.search(linha_n)
        ):
            return _limpar_texto_campo(linha_n)
    return ""


def _cortar_nome_incorporador(valor: str) -> str:
    cortado = valor
    m = _RE_CORTE_MARCADOR_ADMIN.search(valor)
    if m:
        cortado = valor[: m.start()]
    return _limpar_texto_campo(cortado.strip(" -–—"))


def _extrair_incorporador_nome(texto: str) -> str:
    for linha in texto.splitlines():
        m = _RE_INCORPORADOR_ROTULO.search(linha)
        if m:
            nome = _cortar_nome_incorporador(m.group(1))
            if nome:
                return nome
    for linha in texto.splitlines():
        m = _RE_PAGOTTO.search(linha)
        if m:
            nome = _cortar_nome_incorporador(m.group(1))
            if nome:
                return nome
    return ""


def _extrair_nome_edificio(texto: str, designacao: str = "") -> str:
    designacao_norm = designacao.upper().strip()

    def _aceito(nome: str) -> bool:
        if not nome:
            return False
        if nome.upper().startswith("RESIDENCIAL MULTIFAMILIAR"):
            return False
        if designacao_norm and nome.upper() in designacao_norm:
            return False
        return True

    for linha in texto.splitlines():
        m = _RE_NOME_EDIFICIO_ROTULO.search(linha)
        if m:
            nome = _limpar_texto_campo(m.group(1))
            if _aceito(nome):
                return nome
    for linha in texto.splitlines():
        linha_n = _normalizar_linha_ocr(linha)
        if linha_n.upper().startswith("EDIFICAÇÃO") or linha_n.upper().startswith(
            "EDIFICACAO"
        ):
            continue
        m = _RE_EDIFICIO_LINHA.match(linha_n)
        if m:
            nome = _limpar_texto_campo(m.group(1))
            if _aceito(nome):
                return nome
    return ""


def _extrair_processo_aprovacao(texto: str) -> str:
    m = _RE_PROCESSO_APROVACAO.search(texto)
    if not m:
        return ""
    return _limpar_texto_campo(f"Processo Aprovação nº {m.group(1)}")


def _montar_outras_indicacoes(dados: dict, texto: str) -> str:
    partes: list[str] = []
    processo = _extrair_processo_aprovacao(texto)
    if processo:
        partes.append(processo)
    alvara = dados["projeto"].get("numAlvara", "")
    if alvara:
        partes.append(f"Alvará {alvara}")
    local = dados["projeto"].get("localConstrucao", "")
    if local:
        partes.append(f"Local: {local}")
    return "; ".join(partes)


def _formatar_area_designacao(area: float) -> str:
    texto = f"{area:.4f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _item_unidade_quadro2(area: float, qtd: int) -> dict:
    designacao = ""
    if area > 0:
        designacao = f"Apartamento tipo {_formatar_area_designacao(area)} m²"
    return {
        "designacao": designacao,
        "areaPrivCobPadrao": area,
        "areaPrivCobDifReal": 0,
        "areaPrivCobDifEquiv": 0,
        "areaComumNPCobPadrao": 0,
        "areaComumNPCobDifReal": 0,
        "areaComumNPCobDifEquiv": 0,
        "qtdUnidades": qtd,
        "outrasAreasPriv": 0,
        "areaTerrExcl": 0,
        "areaTerrComum": 0,
    }


def _coletar_unidades(texto: str) -> list[tuple[float, int]]:
    """Coleta pares (area, qtd) deduplicados; area 0 para APTOS sem metragem."""
    vistos: dict[tuple[float, int], None] = {}
    linhas_vistas: set[str] = set()

    for linha_raw in texto.splitlines():
        linha = _normalizar_linha_ocr(linha_raw)
        if not linha or linha in linhas_vistas:
            continue
        linhas_vistas.add(linha)

        teve_area_x = False
        for m in _RE_AREA_X_APTOS.finditer(linha):
            teve_area_x = True
            area = round(_parse_numero_br(m.group("area")), 3)
            qtd = int(m.group("qtd"))
            if qtd > 0:
                vistos[(area, qtd)] = None

        if not teve_area_x and not _RE_APTOS_POR_PAV.search(linha):
            for m in _RE_QTD_APTOS.finditer(linha):
                qtd = int(m.group("qtd"))
                if qtd > 0:
                    vistos[(0.0, qtd)] = None

    pares = list(vistos.keys())
    qtds_com_area = {q for a, q in pares if a > 0}
    if qtds_com_area:
        pares = [(a, q) for a, q in pares if a > 0 or q not in qtds_com_area]
    return sorted(pares, key=lambda par: (par[0], par[1]))


def _extrair_unidades_quadro2(texto: str) -> list[dict]:
    pares_com_area = [(a, q) for a, q in _coletar_unidades(texto) if a > 0]
    if not pares_com_area:
        return [_item_unidade_quadro2(0, 1)]
    return [_item_unidade_quadro2(area, qtd) for area, qtd in pares_com_area]


def _extrair_qtd_unidades(texto: str) -> int:
    return sum(qtd for _, qtd in _coletar_unidades(texto))


def _extrair_num_pavimentos(texto: str) -> int:
    base = 0
    m_intervalo = _RE_INTERVALO_PAV.search(texto)
    if m_intervalo:
        base = max(int(m_intervalo.group(1)), int(m_intervalo.group(2)))
    else:
        m_total = _RE_N_PAVIMENTOS.search(texto)
        if m_total:
            base = int(m_total.group(1))

    if base == 0:
        return 0

    extra = 0
    if _RE_TERREO.search(texto):
        extra += 1
    if _RE_COBERTURA.search(texto):
        extra += 1
    return base + extra


def _extrair_vagas_comuns(texto: str) -> int:
    valores = [int(v) for v in _RE_VAGAS_COMUNS.findall(texto)]
    return max(valores) if valores else 0


def _extrair_vagas_duplas(texto: str) -> int:
    valores = [int(v) for v in _RE_VAGAS_DUPLAS.findall(texto)]
    return max(valores) if valores else 0


def _preencher_quadro5(dados: dict, texto: str) -> None:
    q5 = dados["quadro5"]
    proj = dados["projeto"]
    designacao = dados["quadro3"]["projetoPadrao"]["designacao"]

    q5["tipoEdificacao"] = designacao
    q5["dataAprovacao"] = proj["dataAprovacao"]
    q5["numPavimentos"] = (
        str(proj["numPavimentos"]) if proj["numPavimentos"] > 0 else ""
    )

    m_pav = _RE_APTOS_POR_PAV.search(texto)
    q5["unidadesPorPav"] = f"{m_pav.group(1)} APTOS/PAV" if m_pav else ""

    partes_garagem: list[str] = []
    if proj["vagasComum"] > 0:
        partes_garagem.append(f"{proj['vagasComum']} vagas comuns")
    if proj["vagasAcessorio"] > 0:
        partes_garagem.append(f"{proj['vagasAcessorio']} vagas duplas")
    q5["garagens"] = "; ".join(partes_garagem)
    q5["outrasIndicacoes"] = _montar_outras_indicacoes(dados, texto)


def _texto_menciona_vagas_comuns(texto: str) -> bool:
    return bool(re.search(r"VAGAS\s+COMUNS?", texto, re.IGNORECASE))


def _texto_menciona_vagas_duplas(texto: str) -> bool:
    return bool(re.search(r"VAGAS\s+DUPLAS?", texto, re.IGNORECASE))


def _texto_menciona_aptos(texto: str) -> bool:
    return bool(re.search(r"APTOS?|APARTAMENTOS?", texto, re.IGNORECASE))


def _quadro2_apenas_template(unidades: list[dict]) -> bool:
    if len(unidades) != 1:
        return False
    u = unidades[0]
    return not u.get("designacao") and u.get("areaPrivCobPadrao", 0) == 0


def _texto_menciona_incorporador(texto: str) -> bool:
    return bool(
        re.search(
            r"INCORPORADOR|INCORPORADORA|CONSTRUTORA|PROPRIET[AÁ]RIO|PAGOTTO",
            texto,
            re.IGNORECASE,
        )
    )


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
    if not inc.get("nome") and _texto_menciona_incorporador(texto):
        faltantes.append("incorporador.nome")
    if _texto_menciona_crea(texto) and not resp.get("nome"):
        faltantes.append("responsavel.nome")
    if not proj.get("localConstrucao") and _texto_menciona_local_obra(texto):
        faltantes.append("projeto.localConstrucao")
    if not proj.get("nomeEdificio") and _texto_menciona_nome_edificio(texto):
        faltantes.append("projeto.nomeEdificio")

    return faltantes


def extrair_dados_deterministico(texto: str) -> dict:
    """Extrai campos do texto e retorna dict no schema de dados_extraidos.json."""
    dados = _esqueleto_vazio()

    # Task 1: campos base
    dados["incorporador"]["cnpj"] = _extrair_cnpj(texto)
    dados["projeto"]["cidadeUf"] = _extrair_cidade_uf(texto)
    dados["projeto"]["dataAprovacao"] = _extrair_data_aprovacao(texto)
    dados["projeto"]["numAlvara"] = _extrair_num_alvara(texto)
    dados["projeto"]["areaTerreno"] = _extrair_area_terreno(texto)
    dados["projeto"]["projetoPadrao"]["R"] = _detectar_padrao_r(texto)
    designacao = _extrair_designacao(texto)
    dados["quadro3"]["projetoPadrao"]["designacao"] = designacao

    # Task 2: unidades, pavimentos, vagas
    dados["quadro2"]["unidades"] = _extrair_unidades_quadro2(texto)
    dados["projeto"]["qtdUnidades"] = _extrair_qtd_unidades(texto)
    dados["projeto"]["numPavimentos"] = _extrair_num_pavimentos(texto)
    dados["projeto"]["vagasComum"] = _extrair_vagas_comuns(texto)
    dados["projeto"]["vagasAcessorio"] = _extrair_vagas_duplas(texto)

    # Task 3: local, responsavel, incorporador, edificio
    dados["projeto"]["localConstrucao"] = _extrair_local_construcao(texto)
    dados["responsavel"]["crea"] = _extrair_crea(texto)
    dados["responsavel"]["nome"] = _extrair_responsavel_nome(
        texto, dados["responsavel"]["crea"]
    )
    dados["responsavel"]["endereco"] = _extrair_responsavel_endereco(texto)
    dados["incorporador"]["nome"] = _extrair_incorporador_nome(texto)
    dados["projeto"]["nomeEdificio"] = _extrair_nome_edificio(texto, designacao)

    _preencher_quadro5(dados, texto)
    dados["_dados_faltantes"] = _computar_dados_faltantes(dados, texto)

    return dados
