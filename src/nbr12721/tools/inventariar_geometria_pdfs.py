"""CLI diagnostica para inventariar texto e vetores de pranchas PDF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.documents.pdf_geometry import inventariar_pdf
from nbr12721.settings.config import PASTA_DOCS, PASTA_SAIDA


PADROES_TIPO = ("PLA-TIPO", "TIPO_TORRE")


def _pdfs_entrada(pasta: Path, apenas_tipo: bool) -> list[Path]:
    pdfs = sorted(pasta.glob("*.pdf"))
    if not apenas_tipo:
        return pdfs
    return [p for p in pdfs if any(padrao in p.name.upper() for padrao in PADROES_TIPO)]


def _caminho_saida_pdf(pasta_saida: Path, pdf: Path) -> Path:
    return pasta_saida / f"{pdf.stem}.geometria.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera inventarios JSON com textos, linhas, retangulos e curvas de PDFs."
    )
    parser.add_argument("--entrada", default=PASTA_DOCS, help="Pasta com PDFs de entrada.")
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_pdf"),
        help="Pasta onde os JSONs de inventario serao gravados.",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Inventaria todos os PDFs; por padrao usa apenas pranchas tipo.",
    )
    parser.add_argument(
        "--max-paginas",
        type=int,
        default=None,
        help="Limita a quantidade de paginas por PDF para diagnostico rapido.",
    )
    args = parser.parse_args()

    pasta_entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)

    resultados = []
    for pdf in _pdfs_entrada(pasta_entrada, apenas_tipo=not args.todos):
        inventario = inventariar_pdf(pdf, max_paginas=args.max_paginas)
        destino = _caminho_saida_pdf(pasta_saida, pdf)
        destino.write_text(json.dumps(inventario, ensure_ascii=False, indent=2), encoding="utf-8")
        resultados.append((pdf.name, destino, inventario["page_count"]))
        print(f"{pdf.name}: {inventario['page_count']} pagina(s) -> {destino}")

    if not resultados:
        print(f"Nenhum PDF encontrado em {pasta_entrada}")


if __name__ == "__main__":
    main()

