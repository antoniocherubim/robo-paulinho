"""CLI diagnostica para gerar SVGs interpretados da classificacao vetorial."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.settings.config import PASTA_SAIDA
from nbr12721.tools.vector_classification_debug_svg import (
    DEFAULT_MAX_CURVES,
    DEFAULT_MAX_NOISE,
    DEFAULT_MAX_RECTS,
    DEFAULT_MAX_WALL_CANDIDATES,
    LimitesClassificacaoSvg,
    _stem_classificacao,
    salvar_svgs_classificacao,
)


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.classificada.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera SVGs interpretados a partir de inventarios classificados vetorialmente."
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_classificada"),
        help="Pasta com *.classificada.json ou caminho de um unico arquivo classificado.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_classificada_debug"),
        help="Pasta onde os SVGs interpretados serao gravados.",
    )
    parser.add_argument(
        "--mostrar-axis-aligned",
        action="store_true",
        help="Renderiza roll-up axis_aligned_segments com opacidade baixa.",
    )
    parser.add_argument(
        "--max-wall-candidates",
        type=int,
        default=DEFAULT_MAX_WALL_CANDIDATES,
        help=f"Limite de wall_candidates por pagina (padrao: {DEFAULT_MAX_WALL_CANDIDATES}).",
    )
    parser.add_argument(
        "--max-noise",
        type=int,
        default=DEFAULT_MAX_NOISE,
        help=f"Limite total de linhas de ruido por pagina (padrao: {DEFAULT_MAX_NOISE}).",
    )
    parser.add_argument(
        "--max-rects",
        type=int,
        default=DEFAULT_MAX_RECTS,
        help=f"Limite de rect_candidates por pagina (padrao: {DEFAULT_MAX_RECTS}).",
    )
    parser.add_argument(
        "--max-curves",
        type=int,
        default=DEFAULT_MAX_CURVES,
        help=f"Limite de curve_candidates por pagina (padrao: {DEFAULT_MAX_CURVES}).",
    )
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    limites = LimitesClassificacaoSvg(
        max_wall_candidates=max(0, args.max_wall_candidates),
        max_noise=max(0, args.max_noise),
        max_rects=max(0, args.max_rects),
        max_curves=max(0, args.max_curves),
    )

    arquivos = _resolver_entradas(entrada)
    if not arquivos:
        if entrada.is_file():
            print(f"Arquivo classificado nao encontrado: {entrada}")
        else:
            print(f"Nenhum *.classificada.json encontrado em {entrada}")
        return

    pasta_saida.mkdir(parents=True, exist_ok=True)
    for arquivo in arquivos:
        classificacao = json.loads(arquivo.read_text(encoding="utf-8"))
        stem = _stem_classificacao(classificacao.get("file_name"), caminho_json=arquivo)
        destinos = salvar_svgs_classificacao(
            classificacao,
            pasta_saida,
            stem=stem,
            mostrar_axis_aligned=args.mostrar_axis_aligned,
            limites=limites,
        )
        print(f"{arquivo.name}: {len(destinos)} pagina(s) -> {pasta_saida}")
        for destino in destinos:
            print(f"  {destino.name}")


if __name__ == "__main__":
    main()
