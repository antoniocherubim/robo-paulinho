import unittest
from typing import Any, Iterator

from nbr12721.extraction.deterministic_extraction.schema import _esqueleto_vazio
from nbr12721.extraction.field_responsibility import (
    CAMPOS_RESPONSABILIDADE,
    ORIGEM_DETERMINISTICA,
    ORIGEM_FORMULA_EXCEL,
    ORIGEM_LLM,
    ORIGEM_REVISAO_MANUAL,
    campos_por_origem,
    campos_llm_editaveis,
    llm_pode_alterar,
    origem_do_campo,
    path_coberto_pela_matriz,
)


def _iter_folhas_schema(valor: Any, prefixo: str = "") -> Iterator[str]:
    """Percorre o esqueleto canonico; listas contam como folha (path da lista)."""
    if isinstance(valor, dict):
        for chave, filho in valor.items():
            if chave.startswith("_"):
                continue
            path = f"{prefixo}.{chave}" if prefixo else chave
            if isinstance(filho, dict):
                yield from _iter_folhas_schema(filho, path)
            elif isinstance(filho, list):
                yield path
            else:
                yield path

_PATHS_MINIMOS_SPEC: frozenset[str] = frozenset(
    {
        "incorporador.nome",
        "incorporador.cnpj",
        "incorporador.endereco",
        "responsavel.nome",
        "responsavel.crea",
        "responsavel.art",
        "responsavel.endereco",
        "projeto.nomeEdificio",
        "projeto.localConstrucao",
        "projeto.cidadeUf",
        "projeto.qtdUnidades",
        "projeto.numPavimentos",
        "projeto.vagasUA",
        "projeto.vagasAcessorio",
        "projeto.vagasComum",
        "projeto.areaTerreno",
        "projeto.dataAprovacao",
        "projeto.numAlvara",
        "projeto.padraoAcabamento",
        "projeto.projetoPadrao.R",
        "projeto.projetoPadrao.CS",
        "projeto.projetoPadrao.CL",
        "projeto.projetoPadrao.CG",
        "projeto.projetoPadrao.CP",
        "projeto.projetoPadrao.CP1Q",
        "quadro1.pavimentos",
        "quadro2.unidades",
        "quadro3.valorCub",
        "quadro3.sindicato",
        "quadro3.mesCub",
        "quadro3.projetoPadrao.designacao",
        "quadro3.percentuais_e_adicionais",
        "quadro3.percMateriais",
        "quadro4a.unidadesSubrogadas",
        "quadro5.garagens",
        "quadro5.tipoEdificacao",
        "quadro6.equipamentos",
        "quadro7.acabamentos",
        "quadro8.acabamentos",
    }
)


class TestFieldResponsibility(unittest.TestCase):
    def test_campos_criticos_nao_editaveis_por_llm(self):
        for path in (
            "incorporador.cnpj",
            "projeto.qtdUnidades",
            "quadro1.pavimentos",
            "quadro2.unidades",
            "quadro3.valorCub",
        ):
            with self.subTest(path=path):
                self.assertFalse(llm_pode_alterar(path))

    def test_campos_descritivos_editaveis_por_llm(self):
        for path in (
            "incorporador.nome",
            "projeto.nomeEdificio",
            "projeto.localConstrucao",
        ):
            with self.subTest(path=path):
                self.assertTrue(llm_pode_alterar(path))

    def test_campos_por_origem(self):
        llm = campos_por_origem(ORIGEM_LLM)
        paths_llm = {entrada["path"] for entrada in llm}
        self.assertEqual(
            paths_llm,
            {"quadro6.equipamentos", "quadro7.acabamentos", "quadro8.acabamentos"},
        )

        deterministicos = campos_por_origem(ORIGEM_DETERMINISTICA)
        self.assertGreaterEqual(len(deterministicos), 20)

        with self.assertRaises(ValueError):
            campos_por_origem("origem_inexistente")

    def test_prefixo_wildcard_quadro5(self):
        self.assertFalse(llm_pode_alterar("quadro5.tipoEdificacao"))
        self.assertFalse(llm_pode_alterar("quadro5.numeracao"))
        self.assertFalse(llm_pode_alterar("quadro5.garagens"))

    def test_matriz_tem_paths_minimos(self):
        for path in _PATHS_MINIMOS_SPEC:
            with self.subTest(path=path):
                self.assertTrue(
                    path_coberto_pela_matriz(path),
                    f"Path minimo ausente da matriz: {path}",
                )

    def test_campos_llm_editaveis_lista_esperada(self):
        editaveis = set(campos_llm_editaveis())
        self.assertIn("incorporador.nome", editaveis)
        self.assertIn("quadro6.equipamentos", editaveis)
        self.assertNotIn("incorporador.cnpj", editaveis)

    def test_campos_quadro3_cub_e_projeto_padrao_documentados(self):
        self.assertFalse(llm_pode_alterar("quadro3.sindicato"))
        self.assertFalse(llm_pode_alterar("quadro3.mesCub"))
        self.assertFalse(llm_pode_alterar("quadro3.projetoPadrao.areaEquiv"))
        self.assertEqual(origem_do_campo("quadro3.sindicato"), ORIGEM_DETERMINISTICA)
        self.assertEqual(origem_do_campo("quadro3.percMateriais"), ORIGEM_FORMULA_EXCEL)
        self.assertEqual(origem_do_campo("projeto.padraoAcabamento"), ORIGEM_REVISAO_MANUAL)

    def test_matriz_cobre_todas_folhas_do_schema(self):
        folhas = list(_iter_folhas_schema(_esqueleto_vazio()))
        self.assertGreater(len(folhas), 40)
        descobertos: list[str] = []
        for path in folhas:
            if not path_coberto_pela_matriz(path):
                descobertos.append(path)
        self.assertEqual(
            descobertos,
            [],
            f"Folhas do schema sem cobertura na matriz: {descobertos}",
        )


if __name__ == "__main__":
    unittest.main()
