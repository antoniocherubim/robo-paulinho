"""CLI diagnostica para gerar overlays SVG a partir de inventarios geometricos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.settings.config import PASTA_SAIDA
from nbr12721.tools.geometry_debug_svg import (
    DEFAULT_MAX_CURVES,
    DEFAULT_MAX_LINES,
    DEFAULT_MAX_TEXTS,
    LimitesCamada,
    _stem_inventario,
    salvar_svgs_inventario,
)


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.geometria.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera SVGs diagnosticos a partir de inventarios JSON de geometria PDF."
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_pdf"),
        help="Pasta com *.geometria.json ou caminho de um unico inventario.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_debug"),
        help="Pasta onde os SVGs serao gravados.",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Limite de linhas desenhadas por pagina (padrao: {DEFAULT_MAX_LINES}).",
    )
    parser.add_argument(
        "--max-curves",
        type=int,
        default=DEFAULT_MAX_CURVES,
        help=f"Limite de curvas (bbox) por pagina (padrao: {DEFAULT_MAX_CURVES}).",
    )
    parser.add_argument(
        "--max-texts",
        type=int,
        default=DEFAULT_MAX_TEXTS,
        help=f"Limite de textos por pagina (padrao: {DEFAULT_MAX_TEXTS}).",
    )
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    limites = LimitesCamada(
        max_lines=max(0, args.max_lines),
        max_curves=max(0, args.max_curves),
        max_texts=max(0, args.max_texts),
    )

    arquivos = _resolver_entradas(entrada)
    if not arquivos:
        if entrada.is_file():
            print(f"Arquivo de inventario nao encontrado: {entrada}")
        else:
            print(f"Nenhum *.geometria.json encontrado em {entrada}")
        return

    pasta_saida.mkdir(parents=True, exist_ok=True)
    for arquivo in arquivos:
        inventario = json.loads(arquivo.read_text(encoding="utf-8"))
        stem = _stem_inventario(inventario.get("file_name"), caminho_json=arquivo)
        destinos = salvar_svgs_inventario(
            inventario,
            pasta_saida,
            stem=stem,
            limites=limites,
        )
        print(f"{arquivo.name}: {len(destinos)} pagina(s) -> {pasta_saida}")
        for destino in destinos:
            print(f"  {destino.name}")


if __name__ == "__main__":
    main()
