"""CLI diagnostica para detectar regioes/celulas ortogonais a partir de classificacao vetorial."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.documents.region_detection import (
    ParametrosDeteccaoRegioes,
    _stem_classificacao,
    salvar_regioes,
)
from nbr12721.settings.config import PASTA_SAIDA


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.classificada.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Detecta celulas/regioes ortogonais candidatas a partir de "
            "inventarios classificados *.classificada.json."
        )
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_classificada"),
        help="Pasta com *.classificada.json ou caminho de um unico arquivo.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_regioes"),
        help="Pasta onde os JSONs de regioes serao gravados.",
    )
    parser.add_argument("--merge-tolerance", type=float, default=2.0)
    parser.add_argument("--snap-tolerance", type=float, default=3.0)
    parser.add_argument("--min-region-width", type=float, default=8.0)
    parser.add_argument("--min-region-height", type=float, default=8.0)
    parser.add_argument("--min-region-area", type=float, default=100.0)
    parser.add_argument("--max-region-area-ratio", type=float, default=0.25)
    parser.add_argument("--max-regions", type=int, default=5000)
    parser.add_argument("--max-rejected-regions", type=int, default=1000)
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    params = ParametrosDeteccaoRegioes(
        merge_tolerance=max(0.0, args.merge_tolerance),
        snap_tolerance=max(0.0, args.snap_tolerance),
        min_region_width=max(0.0, args.min_region_width),
        min_region_height=max(0.0, args.min_region_height),
        min_region_area=max(0.0, args.min_region_area),
        max_region_area_ratio=max(0.0, min(1.0, args.max_region_area_ratio)),
        max_regions=max(0, args.max_regions),
        max_rejected_regions=max(0, args.max_rejected_regions),
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
        destino = pasta_saida / f"{stem}.regioes.json"
        resultado = salvar_regioes(classificacao, destino, params=params)
        paginas = resultado["pages"]
        total_regions = sum(p["stats"]["candidate_regions"] for p in paginas)
        total_rejected = sum(p["stats"]["rejected_regions"] for p in paginas)
        truncated = any(p.get("truncated") for p in paginas)
        print(
            f"{arquivo.name}: {len(paginas)} pagina(s) -> {destino.name} "
            f"| regioes={total_regions} rejeitadas={total_rejected} truncated={truncated}"
        )


if __name__ == "__main__":
    main()
