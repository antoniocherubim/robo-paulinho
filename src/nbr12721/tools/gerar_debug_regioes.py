"""CLI diagnostica para gerar SVGs de regioes detectadas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.settings.config import PASTA_SAIDA
from nbr12721.tools.region_debug_svg import (
    DEFAULT_MAX_REGIONS_SVG,
    DEFAULT_MAX_REJECTED_SVG,
    LimitesRegioesSvg,
    _stem_regioes,
    salvar_svgs_regioes,
)


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.regioes.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera SVGs diagnosticos a partir de JSONs de regioes detectadas."
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_regioes"),
        help="Pasta com *.regioes.json ou caminho de um unico arquivo.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_regioes_debug"),
        help="Pasta onde os SVGs serao gravados.",
    )
    parser.add_argument(
        "--ocultar-rejeitadas",
        action="store_true",
        help="Nao renderiza rejected_regions (por padrao sao exibidas).",
    )
    parser.add_argument(
        "--ocultar-labels",
        action="store_true",
        help="Oculta labels curtos; centroides permanecem visiveis.",
    )
    parser.add_argument(
        "--max-regions",
        type=int,
        default=DEFAULT_MAX_REGIONS_SVG,
        help=f"Limite de regions renderizadas por pagina (padrao: {DEFAULT_MAX_REGIONS_SVG}).",
    )
    parser.add_argument(
        "--max-rejected",
        type=int,
        default=DEFAULT_MAX_REJECTED_SVG,
        help=f"Limite de rejected_regions renderizadas por pagina (padrao: {DEFAULT_MAX_REJECTED_SVG}).",
    )
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    limites = LimitesRegioesSvg(
        max_regions=max(0, args.max_regions),
        max_rejected=max(0, args.max_rejected),
    )

    arquivos = _resolver_entradas(entrada)
    if not arquivos:
        if entrada.is_file():
            print(f"Arquivo de regioes nao encontrado: {entrada}")
        else:
            print(f"Nenhum *.regioes.json encontrado em {entrada}")
        return

    pasta_saida.mkdir(parents=True, exist_ok=True)
    for arquivo in arquivos:
        regioes_doc = json.loads(arquivo.read_text(encoding="utf-8"))
        stem = _stem_regioes(regioes_doc.get("file_name"), caminho_json=arquivo)
        destinos = salvar_svgs_regioes(
            regioes_doc,
            pasta_saida,
            stem=stem,
            mostrar_rejeitadas=not args.ocultar_rejeitadas,
            mostrar_labels=not args.ocultar_labels,
            limites=limites,
        )
        print(f"{arquivo.name}: {len(destinos)} pagina(s) -> {pasta_saida}")
        for destino in destinos:
            print(f"  {destino.name}")


if __name__ == "__main__":
    main()
