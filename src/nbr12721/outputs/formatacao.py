"""Formatacao de valores para exibicao no pipeline NBR 12721."""

__all__ = ["formatar_brl"]


def formatar_brl(valor):
    return f"{valor:,.2f}".replace(",","X").replace(".",",").replace("X",".")
