"""Validacao de completude do JSON extraido (NBR 12721)."""

from __future__ import annotations

import re

__all__ = ["validar_dados_extraidos"]

_RE_MARCADOR_PDF = re.compile(r"^\[[^\]]+\.pdf\]", re.IGNORECASE)
_RE_FRASES_ADMIN = re.compile(
    r"\b(?:CERTIFICADO\s+DE\s+VISTORIA|HABITE-?SE|"
    r"FICARA\s+CONDICIONAD|FICARA\s+CONDICINAD)\b",
    re.IGNORECASE,
)
_RE_CIDADE_UF = re.compile(
    r"\b[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\s]{1,40}[-/][A-Z]{2}\b",
    re.IGNORECASE,
)
_RE_CREA = re.compile(
    r"\b[A-Z]{2}\s*[-/]?\s*\d{4,6}\s*/?\s*[A-Z]?\b",
    re.IGNORECASE,
)
_RE_SUFIXO_EMPRESA = re.compile(
    r"\b(?:LTDA|S/?A|SPE|EIRELI)\b",
    re.IGNORECASE,
)

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


def _validar_quadro1_area_tipo(dados: dict) -> list[str]:
    """Detecta area total do conjunto lancada como area unitaria no pavimento tipo."""
    inconsistencias: list[str] = []
    pavimentos = _get_path(dados, "quadro1.pavimentos")
    unidades = _get_path(dados, "quadro2.unidades")
    qtd_unidades_projeto = _get_path(dados, "projeto.qtdUnidades")

    if not isinstance(pavimentos, list) or not isinstance(unidades, list):
        return inconsistencias
    if not isinstance(qtd_unidades_projeto, (int, float)) or qtd_unidades_projeto <= 0:
        return inconsistencias

    area_unidades_total = sum(
        float(u.get("areaPrivCobPadrao", 0) or 0)
        * float(u.get("qtdUnidades", 0) or 0)
        for u in unidades
        if isinstance(u, dict)
    )
    if area_unidades_total <= 0:
        return inconsistencias

    for pav in pavimentos:
        if not isinstance(pav, dict):
            continue
        nome = str(pav.get("nome", ""))
        if "tipo" not in nome.lower():
            continue
        qtd_pav = int(pav.get("qtdPavimentos", 0) or 0)
        area_pav = float(pav.get("areaPrivCobPadrao", 0) or 0)
        if qtd_pav <= 1 or area_pav <= 0:
            continue
        area_tipo_total = area_pav * qtd_pav
        if area_tipo_total > area_unidades_total * 1.5:
            inconsistencias.append(
                "quadro1.pavimentos.area_tipo_possivelmente_total_duplicada"
            )
            break

    return inconsistencias


def _texto_parece_lixo_ocr(valor: str) -> bool:
    """True se o texto preenchido parece residuo OCR, nao dado semantico util."""
    texto = str(valor).strip()
    if not texto:
        return False
    if _RE_SUFIXO_EMPRESA.search(texto) and _RE_CIDADE_UF.search(texto):
        return False
    if _RE_SUFIXO_EMPRESA.search(texto) and len(texto) > 12:
        return False
    if _RE_CIDADE_UF.fullmatch(texto) or _RE_CIDADE_UF.search(texto):
        if not _RE_FRASES_ADMIN.search(texto) and not texto.lstrip().startswith(","):
            return False
    if _RE_CREA.search(texto) and not _RE_FRASES_ADMIN.search(texto):
        return False
    if re.match(r"^[,;.:|\-_–—]+\s*\S", texto):
        return True
    if _RE_MARCADOR_PDF.search(texto):
        return True
    if _RE_FRASES_ADMIN.search(texto):
        return True
    letras = len(re.findall(r"[A-Za-zÀ-ÿ]", texto, re.IGNORECASE))
    simbolos = len(re.findall(r"[^A-Za-zÀ-ÿ0-9\s]", texto))
    if letras > 0 and simbolos / letras > 0.4:
        return True
    return False


def _texto_contem_marcador_pdf(valor: str) -> bool:
    return bool(_RE_MARCADOR_PDF.search(str(valor).strip()))


def _item_template_vazio(item: dict, campos: tuple[str, ...]) -> bool:
    if not isinstance(item, dict):
        return True
    for campo in campos:
        valor = item.get(campo)
        if isinstance(valor, str):
            if valor.strip():
                return False
        elif isinstance(valor, (int, float)):
            if valor != 0:
                return False
        elif valor:
            return False
    return True


def _lista_template_vazia(
    dados: dict, path: str, campos: tuple[str, ...]
) -> bool:
    itens = _get_path(dados, path)
    if not isinstance(itens, list) or len(itens) == 0:
        return False
    return all(
        _item_template_vazio(item, campos) for item in itens if isinstance(item, dict)
    )


def _validar_semantica_textual(dados: dict) -> list[str]:
    avisos: list[str] = []
    checks = (
        ("projeto.nomeEdificio", "projeto.nomeEdificio.lixo_ocr", _texto_parece_lixo_ocr),
        ("incorporador.nome", "incorporador.nome.lixo_ocr", _texto_parece_lixo_ocr),
        ("projeto.localConstrucao", "projeto.localConstrucao.lixo_ocr", _texto_parece_lixo_ocr),
    )
    for path, codigo, fn in checks:
        valor = _get_path(dados, path)
        if isinstance(valor, str) and valor.strip() and fn(valor):
            avisos.append(codigo)
    endereco = _get_path(dados, "responsavel.endereco")
    if isinstance(endereco, str) and endereco.strip() and _texto_contem_marcador_pdf(endereco):
        avisos.append("responsavel.endereco.lixo_ocr")
    return avisos


def _validar_templates_quadros(dados: dict) -> list[str]:
    avisos: list[str] = []
    templates = (
        ("quadro6.equipamentos", ("nome", "tipo", "acabamento", "detalhes")),
        (
            "quadro7.acabamentos",
            ("dependencia", "pisos", "paredes", "tetos", "outros"),
        ),
        (
            "quadro8.acabamentos",
            ("dependencia", "pisos", "paredes", "tetos", "outros"),
        ),
    )
    for path, campos in templates:
        if _lista_template_vazia(dados, path, campos):
            avisos.append(f"{path}.template_vazio")
    return avisos


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
    inconsistencias = _validar_quadro1_area_tipo(dados)
    avisos_semanticos = sorted(
        set(_validar_semantica_textual(dados) + _validar_templates_quadros(dados))
    )
    return {
        "ok": len(criticos_faltantes) == 0,
        "score": score,
        "criticos_faltantes": criticos_faltantes,
        "avisos": avisos,
        "inconsistencias": inconsistencias,
        "avisos_semanticos": avisos_semanticos,
    }
