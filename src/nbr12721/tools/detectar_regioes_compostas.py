"""CLI diagnostica para detectar regioes compostas a partir de regioes detectadas."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.documents.composite_region_detection import (
    ParametrosRegioesCompostas,
    _stem_regioes,
    salvar_regioes_compostas,
)
from nbr12721.settings.config import PASTA_SAIDA


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.regioes.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Detecta regioes compostas candidatas a partir de inventarios "
            "*.regioes.json (celulas fechadas adjacentes)."
        )
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_regioes"),
        help="Pasta com *.regioes.json ou caminho de um unico arquivo.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_regioes_compostas"),
        help="Pasta onde os JSONs de regioes compostas serao gravados.",
    )
    parser.add_argument("--adjacency-tolerance", type=float, default=3.0)
    parser.add_argument("--min-composite-width", type=float, default=20.0)
    parser.add_argument("--min-composite-height", type=float, default=20.0)
    parser.add_argument("--min-composite-area", type=float, default=400.0)
    parser.add_argument("--min-fill-ratio", type=float, default=0.05)
    parser.add_argument("--max-composite-area-ratio", type=float, default=0.25)
    parser.add_argument("--max-composite-width-ratio", type=float, default=0.50)
    parser.add_argument("--max-composite-height-ratio", type=float, default=0.50)
    parser.add_argument("--max-cells-per-component", type=int, default=200)
    parser.add_argument("--max-composites", type=int, default=5000)
    parser.add_argument("--max-rejected-composites", type=int, default=1000)
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    params = ParametrosRegioesCompostas(
        adjacency_tolerance=max(0.0, args.adjacency_tolerance),
        min_composite_width=max(0.0, args.min_composite_width),
        min_composite_height=max(0.0, args.min_composite_height),
        min_composite_area=max(0.0, args.min_composite_area),
        min_fill_ratio=max(0.0, min(1.0, args.min_fill_ratio)),
        max_composite_area_ratio=max(0.0, min(1.0, args.max_composite_area_ratio)),
        max_composite_width_ratio=max(0.0, min(1.0, args.max_composite_width_ratio)),
        max_composite_height_ratio=max(0.0, min(1.0, args.max_composite_height_ratio)),
        max_cells_per_component=max(1, args.max_cells_per_component),
        max_composites=max(0, args.max_composites),
        max_rejected_composites=max(0, args.max_rejected_composites),
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
        destino = pasta_saida / f"{stem}.regioes_compostas.json"
        resultado = salvar_regioes_compostas(regioes_doc, destino, params=params)
        paginas = resultado["pages"]
        total_base_cells = sum(p["stats"]["base_cells"] for p in paginas)
        total_pair_checks = sum(p["stats"]["pair_checks"] for p in paginas)
        total_adjacency_edges = sum(p["stats"]["adjacency_edges"] for p in paginas)
        total_components = sum(p["stats"]["components_found"] for p in paginas)
        total_composites = sum(p["stats"]["candidate_composites"] for p in paginas)
        total_rejected = sum(p["stats"]["rejected_composites"] for p in paginas)
        truncated = any(p.get("truncated") for p in paginas)
        print(
            f"{arquivo.name}: {len(paginas)} pagina(s) -> {destino.name} "
            f"| base_cells={total_base_cells} pair_checks={total_pair_checks} "
            f"adjacency_edges={total_adjacency_edges} components_found={total_components} "
            f"composite_regions={total_composites} rejected_composites={total_rejected} "
            f"truncated={truncated}"
        )


if __name__ == "__main__":
    main()
