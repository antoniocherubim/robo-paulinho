"""CLI diagnostica para classificar elementos vetoriais de inventarios PDF."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nbr12721.documents.vector_classification import (
    ParametrosClassificacao,
    _stem_inventario,
    salvar_classificacao,
)
from nbr12721.settings.config import PASTA_SAIDA


def _resolver_entradas(caminho: Path) -> list[Path]:
    if caminho.is_file():
        return [caminho]
    if caminho.is_dir():
        return sorted(caminho.glob("*.geometria.json"))
    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Classifica linhas vetoriais em candidatos a parede/contorno e ruidos graficos "
            "a partir de inventarios *.geometria.json."
        )
    )
    parser.add_argument(
        "--entrada",
        default=str(Path(PASTA_SAIDA) / "geometria_pdf"),
        help="Pasta com *.geometria.json ou caminho de um unico inventario.",
    )
    parser.add_argument(
        "--saida",
        default=str(Path(PASTA_SAIDA) / "geometria_classificada"),
        help="Pasta onde os JSONs classificados serao gravados.",
    )
    parser.add_argument(
        "--min-length-wall",
        type=float,
        default=10.0,
        help="Comprimento minimo (pontos) para candidato a parede/contorno (padrao: 10).",
    )
    parser.add_argument(
        "--titleblock-right-ratio",
        type=float,
        default=0.72,
        help="Limite relativo da regiao direita de carimbo (padrao: 0.72).",
    )
    parser.add_argument(
        "--titleblock-bottom-ratio",
        type=float,
        default=0.72,
        help="Limite relativo da regiao inferior de carimbo (padrao: 0.72).",
    )
    parser.add_argument(
        "--text-near-radius",
        type=float,
        default=12.0,
        help="Raio em pontos para contar textos proximos a uma linha (padrao: 12).",
    )
    parser.add_argument(
        "--text-near-min-count",
        type=int,
        default=4,
        help="Minimo de textos proximos para classificar como ruido de tabela/carimbo (padrao: 4).",
    )
    args = parser.parse_args()

    entrada = Path(args.entrada)
    pasta_saida = Path(args.saida)
    params = ParametrosClassificacao(
        min_length_wall=max(0.0, args.min_length_wall),
        titleblock_right_ratio=max(0.0, min(1.0, args.titleblock_right_ratio)),
        titleblock_bottom_ratio=max(0.0, min(1.0, args.titleblock_bottom_ratio)),
        text_near_radius=max(0.0, args.text_near_radius),
        text_near_min_count=max(0, args.text_near_min_count),
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
        destino = pasta_saida / f"{stem}.classificada.json"
        resultado = salvar_classificacao(inventario, destino, params=params)
        paginas = resultado["pages"]
        total_walls = sum(p["stats"]["wall_candidates"] for p in paginas)
        total_noise = sum(p["stats"]["discarded_noise"] for p in paginas)
        print(
            f"{arquivo.name}: {len(paginas)} pagina(s) -> {destino.name} "
            f"| contorno_candidato={total_walls} ruido={total_noise}"
        )


if __name__ == "__main__":
    main()
