import inspect
import unittest


class TestImports(unittest.TestCase):
    def test_todos_os_modulos_importam(self):
        modulos = [
            "nbr12721.config",
            "nbr12721.prompts",
            "nbr12721.formatacao",
            "nbr12721.llm",
            "nbr12721.cub",
            "nbr12721.pdf_processing",
            "nbr12721.serialization",
            "nbr12721.excel_writer",
            "nbr12721.pipeline",
            "nbr12721.main",
            "nbr12721",
        ]
        for nome in modulos:
            with self.subTest(modulo=nome):
                __import__(nome)

    def test_llm_exporta_chamar_llm(self):
        from nbr12721 import llm
        self.assertIn("chamar_llm", llm.__all__)
        self.assertTrue(inspect.iscoroutinefunction(llm.chamar_llm))

    def test_config_exporta_resolvers_llm(self):
        from nbr12721 import config
        for nome in (
            "resolver_llm_provider",
            "resolver_llm_auto_primary",
            "resolver_openai_model",
        ):
            with self.subTest(resolver=nome):
                self.assertTrue(callable(getattr(config, nome)))

    def test_config_paths_padrao(self):
        from nbr12721.config import PASTA_DOCS, PASTA_SAIDA, PLANILHA
        docs = PASTA_DOCS.replace("\\", "/")
        saida = PASTA_SAIDA.replace("\\", "/")
        planilha = PLANILHA.replace("\\", "/")
        self.assertTrue(docs.endswith("data/input/documentos"))
        self.assertTrue(saida.endswith("data/output/saida"))
        self.assertTrue(planilha.endswith("assets/ABNT_NBR_12721-2006.xlsx"))


if __name__ == "__main__":
    unittest.main()
