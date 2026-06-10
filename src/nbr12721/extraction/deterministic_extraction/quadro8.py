"""Preenchimento deterministico conservador do Quadro VIII (acabamentos comuns)."""

from __future__ import annotations

_CAMPOS_SUPERFICIE = ("pisos", "paredes", "tetos", "outros")


def _candidato_quadro8_valido(candidato: dict) -> bool:
    if candidato.get("quadro") != "quadro8":
        return False
    if not str(candidato.get("dependencia", "")).strip():
        return False
    materiais = candidato.get("materiais")
    if not isinstance(materiais, list) or not materiais:
        return False
    if not str(candidato.get("linha", "")).strip():
        return False
    return True


def _juntar_materiais(valores: list[str]) -> str:
    return ", ".join(v for v in valores if v)


def _candidato_para_item_acabamento(candidato: dict) -> dict:
    ctx = candidato.get("materiais_contexto") or {}
    item = {
        "dependencia": candidato["dependencia"],
        "pisos": "",
        "paredes": "",
        "tetos": "",
        "outros": "",
    }

    if ctx:
        for campo in _CAMPOS_SUPERFICIE:
            valores = ctx.get(campo)
            if isinstance(valores, list) and valores:
                item[campo] = _juntar_materiais(valores)
    else:
        item["outros"] = _juntar_materiais(candidato["materiais"])

    return item


def _deduplicar_itens_acabamento(itens: list[dict]) -> list[dict]:
    vistos: set[tuple[str, ...]] = set()
    resultado: list[dict] = []
    for item in itens:
        chave = tuple(
            str(item.get(campo, "")).strip().lower() for campo in ("dependencia", *_CAMPOS_SUPERFICIE)
        )
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(item)
    return resultado


def _preencher_quadro8(dados: dict, texto: str) -> None:
    """Preenche quadro8.acabamentos a partir de candidatos estruturados conservadores."""
    from ...documents.pdf_processing import extrair_candidatos_acabamentos

    candidatos = extrair_candidatos_acabamentos(texto)
    itens = [
        _candidato_para_item_acabamento(c)
        for c in candidatos
        if _candidato_quadro8_valido(c)
    ]
    itens = _deduplicar_itens_acabamento(itens)
    if itens:
        dados["quadro8"]["acabamentos"] = itens
