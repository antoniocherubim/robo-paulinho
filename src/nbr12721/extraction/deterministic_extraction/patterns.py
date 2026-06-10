"""Padroes regex compartilhados pelo extrator deterministico."""

from __future__ import annotations

import re

RE_DATA = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
UFS_BRASIL = frozenset(
    {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
        "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
        "SP", "SE", "TO",
    }
)
RE_PREFIXO_EVIDENCIA_ARQUIVO = re.compile(
    r"^\[[^\]]+\]\s*",
    re.IGNORECASE,
)
RE_LINHA_CIDADE_UF_REJEITADA = re.compile(
    r"^DOCUMENTO:\s*[^\s]+\.pdf\s*$|^(?:ARQ-PL|PLA-)[^\s]*\s*$",
    re.IGNORECASE,
)
_UFS_REGEX = "|".join(sorted(UFS_BRASIL))
RE_CIDADE_UF_EVIDENCIA = re.compile(
    rf"\b[A-ZÀ-Ü][A-ZÀ-Ü ]{{2,}}\s*[-/]\s*({_UFS_REGEX})\b",
    re.IGNORECASE,
)
RE_CIDADE_UF_LINHA = re.compile(
    r"(?<![A-Za-zÀ-ÿ])([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ \t]{2,40}?)[ \t]*[-/][ \t]*([A-Z]{2})\b",
    re.IGNORECASE,
)
RE_CONTEXTO_PROFISSIONAL = re.compile(
    r"\b(?:CREA|CAU|CNPJ)\b",
    re.IGNORECASE,
)
JANELA_LINHAS_DATA_CONTEXTO = 2
RE_ALVARA = re.compile(
    r"(?:N[°ºo.]?\s*DE\s+)?ALVAR[AÁ]\s*:?\s*([0-9]+(?:\s*/\s*[0-9]+)?)",
    re.IGNORECASE,
)
RE_TERRENO = re.compile(
    r"TERRENO\s*:\s*([\d.,]+)\s*M",
    re.IGNORECASE,
)
RE_AREA_TERRENO_AT = re.compile(
    r"(?:ÁREA|AREA)\s+TERRENO\s*\[AT\]\s*[=|:|]?\s*([\d.,]+)",
    re.IGNORECASE,
)
RE_TERRENO_M2 = re.compile(
    r"TERRENO\s+([\d.,]+)\s*M\s*2",
    re.IGNORECASE,
)
RE_PROPRIEDADE_TERRENO = re.compile(
    r"PROPRIEDADE\s+DO\s+TERRENO",
    re.IGNORECASE,
)
RE_LOCAL_CABECALHO = re.compile(
    r"DATA\s+DO\s+PROJETO|TAXA\s+DE\s+OCUPA[CÇ][AÃ]O",
    re.IGNORECASE,
)
RE_LOTE = re.compile(r"\bLOTE\b", re.IGNORECASE)
RE_LOCAL_KEYWORDS = re.compile(
    r"\b(?:LOTE|QUADRA|RUA|AVENIDA|AV\.|ESTRADA|RODOVIA|FAZENDA|GLEBA|"
    r"CH[AÁ]CARA|S[IÍ]TIO|CONDOM[IÍ]NIO|BAIRRO|SITUAD|LOCALIZAD|MATR[IÍ]CULA)\b",
    re.IGNORECASE,
)
RE_SITUADO_NO = re.compile(
    r"SITUAD[OA]\s+NO\s+(.+)",
    re.IGNORECASE,
)
RE_TAXA_PERCENTUAL_FINAL = re.compile(r",\s*[\d.,]+\s*%\s*$")
RE_BLOCO_ADMINISTRATIVO = re.compile(
    r"\b(?:Processo|Aprova[cç][aã]o|Alvar[aá]|Diretoria|Matr[ií]cula|"
    r"Assinado|Digitalmente|Digital|Dados)\b",
    re.IGNORECASE,
)
RE_CNPJ_ROTULADO = re.compile(
    r"CNPJ\s*(\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}|\d{2}\.?\d{3}\.?\d{3}\d{4}-?\d{2})",
    re.IGNORECASE,
)
RE_LINHA_CNPJ = re.compile(
    r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b|"
    r"\b\d{2}\.\d{3}\.\d{3}\d{4}-\d{2}\b",
    re.IGNORECASE,
)
RE_PREFIXO_ARQUIVO_PDF = re.compile(
    r"^\[[^\]]+\.pdf\]\s*",
    re.IGNORECASE,
)
RE_LIXO_NOME_EDIFICIO = re.compile(
    r"\b(?:CERTIFICADO\s+DE\s+VISTORIA|HABITE-?SE|"
    r"FICARA\s+CONDIC\w*|CONDICIONAD\w*|CONDIEINAD\w*)\b|^\s*[,;:\-–—]",
    re.IGNORECASE,
)


def linha_contem_cnpj(linha: str) -> bool:
    """True quando a linha tem CNPJ rotulado ou mascarado (nao CPF nem data)."""
    return bool(RE_CNPJ_ROTULADO.search(linha) or RE_LINHA_CNPJ.search(linha))


RE_EMPRESA_JURIDICA = re.compile(
    r"\b(?:LTDA|S/?A\.?|SA|EIRELI|SPE|INCORPORA[CÇ][AÃ]O|CONSTRU[CÇ][AÃ]O|"
    r"EMPREENDIMENTOS)\b",
    re.IGNORECASE,
)
RE_MENCAO_ROTULO_INCORPORADOR = re.compile(
    r"\b(?:INCORPORADOR|INCORPORADORA|CONSTRUTORA|"
    r"PROPRIET[AÁ]RIO(?:\s+DO\s+TERRENO)?|PROPRIETARIA)\b",
    re.IGNORECASE,
)
RE_NOME_RESP_INVALIDO = re.compile(
    r"\b(?:Processo|Aprova[cç][aã]o|Alvar[aá]|CNPJ|CPF|Diretoria|Assinado|"
    r"Digital|Dados|Matr[ií]cula|Propriet[aá]rio|RESPONS[AÁ]VEL|N[°ºo.])\b",
    re.IGNORECASE,
)
RE_CPF_CNPJ_DATA_NOME = re.compile(
    r"\b(?:CPF|CNPJ)\b|\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b",
    re.IGNORECASE,
)
RE_DESIGNACAO = re.compile(
    r"(EDIFICA[CÇ][AÃ]O\s+RESIDENCIAL\s+MULTIFAMILIAR\s+VERTICAL\s*\[RMV\])",
    re.IGNORECASE,
)
RE_CNPJ_DIGITOS = re.compile(r"\d")
RE_CREA = re.compile(
    r"CREA\s*([A-Z]{2})\s*[-/]?\s*(\d{4,6})\s*[/]?\s*([A-Z])?",
    re.IGNORECASE,
)
RE_CREA_COLADO = re.compile(
    r"CREA\s*([A-Z]{2})\s*[-]?\s*(\d{4,6})\s*([A-Z])?",
    re.IGNORECASE,
)
PALAVRAS_DATA_CONTEXTO = re.compile(
    r"aprova[cç][aã]o|aprovacao|alvar[aá]|alvara|data\s+do\s+projeto",
    re.IGNORECASE,
)
PALAVRAS_PADRAO_R = re.compile(
    r"residencial.*(?:multifamiliar|vertical|\[rmv\])|"
    r"(?:multifamiliar|vertical|\[rmv\]).*residencial",
    re.IGNORECASE,
)
RE_AREA_X_APTOS = re.compile(
    r"(?P<area>[\d.,]+)\s*[xX×]\s*(?P<qtd>\d+)\s*(?:APTOS?|APARTAMENTOS?)\b",
    re.IGNORECASE,
)
RE_QTD_APTOS = re.compile(
    r"(?<![\d.,])\b(?P<qtd>\d+)\s*(?:APTOS?|APARTAMENTOS?)(?!/\s*PAV)\b",
    re.IGNORECASE,
)
RE_INTERVALO_PAV = re.compile(
    r"\b(\d+)\s*(?:º|°)?\s*AO\s*(\d+)\s*(?:º|°)?\b",
    re.IGNORECASE,
)
RE_N_PAVIMENTOS = re.compile(r"\b(\d+)\s+PAVIMENTOS?\b", re.IGNORECASE)
RE_TERREO = re.compile(
    r"PAVIMENTO\s+T[EÉ]RREO|\bT[EÉ]RREO\b",
    re.IGNORECASE,
)
RE_COBERTURA = re.compile(r"\bCOBERTURA\b", re.IGNORECASE)
RE_VAGAS_COMUNS = re.compile(
    r"TOTAL\s+DE\s+VAGAS\s+COMUNS?\s*[:.]?\s*(\d+)",
    re.IGNORECASE,
)
RE_VAGAS_DUPLAS = re.compile(
    r"TOTAL\s+DE\s+VAGAS\s+DUPLAS?\s*[:.]?\s*(\d+)",
    re.IGNORECASE,
)
RE_APTOS_POR_PAV = re.compile(
    r"\b(\d+)\s*APTOS?\s*/\s*PAV\b",
    re.IGNORECASE,
)
RE_LOCAL_OBRA = re.compile(
    r"LOCAL\s+DA\s+OBRA\s*:?\s*(.+)",
    re.IGNORECASE,
)
RE_ENDERECO_OBRA = re.compile(
    r"ENDE[RRE][CÇ]O\s+DA\s+OBRA\s*:?\s*(.+)",
    re.IGNORECASE,
)
RE_SITUADO = re.compile(
    r"^SITUAD[OA]\s+NO\s+(.+)",
    re.IGNORECASE,
)
RE_PROCESSO_APROVACAO = re.compile(
    r"Processo\s+Aprova[cç][aã]o\s+n[°ºo.]?\s*([\d./-]+)",
    re.IGNORECASE,
)
RE_INCORPORADOR_ROTULO = re.compile(
    r"^\s*(?:INCORPORADOR|INCORPORADORA|CONSTRUTORA|"
    r"PROPRIET[AÁ]RIO(?:\s+DO\s+TERRENO)?|PROPRIETARIA)\s*:?\s*(.+)",
    re.IGNORECASE,
)
RE_CORTE_MARCADOR_ADMIN = re.compile(
    r"\b(?:Processo|N[°ºo.]|ALVAR[AÁ]|CREA|CAU|CNPJ)\b",
    re.IGNORECASE,
)
RE_NOME_EDIFICIO_ROTULO = re.compile(
    r"(?:NOME\s+DO\s+EDIF[IÍ]CIO|EMPREENDIMENTO)\s*:?\s*(.+)",
    re.IGNORECASE,
)
RE_EDIFICIO_LINHA = re.compile(
    r"^EDIF[IÍ]CIO\s+(.+)",
    re.IGNORECASE,
)
RE_PROFISSAO_SPLIT = re.compile(
    r"\b(?:ENGENHEIR[OA]|ARQUITET[OA]|CREA|CAU)\b",
    re.IGNORECASE,
)
RE_PROFISSAO_NOME = re.compile(
    r"\b(?:ENGENHEIR[OA]|ARQUITET[OA])(?:\s+CIVIL|\s+URBANISTA)?\b",
    re.IGNORECASE,
)
RE_LOGRADOURO = re.compile(
    r"\b(?:rua|avenida|av\.|travessa|alameda)\b",
    re.IGNORECASE,
)
RE_CEP = re.compile(r"\d{5}-?\d{3}")
RE_TEL = re.compile(r"\[\d+\]")
RE_EMAIL = re.compile(r"@")
RE_AREA_LAZER_COBERTA_TERREO = re.compile(
    r"[AÁ]REA\s+DE\s+LAZER\s+COBERTA.*?T[EÉ]RREO\s*=\s*([\d.,]+)\s*m",
    re.IGNORECASE,
)
RE_AREA_LAZER_DESCOBERTA_TERREO = re.compile(
    r"[AÁ]REA\s+DE\s+LAZER\s+DESCOBERTA.*?T[EÉ]RREO\s*=\s*([\d.,]+)\s*m",
    re.IGNORECASE,
)
RE_AREA_PAV_TERREO = re.compile(
    r"[AÁ]REA\s+PAV(?:IMENTO|\.)?\s*T[EÉ]RREO\s*:?\s*([\d.,]+)\s*m",
    re.IGNORECASE,
)
RE_AREA_COBERTURA = re.compile(
    r"(?:COBERTURA.*?[AÁ]REA|[AÁ]REA\s+COBERTURA)\s*:?\s*([\d.,]+)\s*m",
    re.IGNORECASE,
)
RE_PAV_TIPO_LINHA = re.compile(r"PAV\.?\s*TIPO", re.IGNORECASE)

NOME_PAVIMENTOS_TIPO = "Pavimentos tipo"
NOME_PAVIMENTO_TERREO = "Pavimento térreo"
NOME_COBERTURA = "Cobertura"
