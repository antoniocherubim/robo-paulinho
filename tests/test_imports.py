import inspect
import unittest


class TestImports(unittest.TestCase):
    def test_todos_os_modulos_importam(self):
        modulos = [
            "nbr12721.documents",
            "nbr12721.documents.pdf_processing",
            "nbr12721.extraction",
            "nbr12721.extraction.deterministic_extraction",
            "nbr12721.extraction.deterministic_extraction.extractor",
            "nbr12721.extraction.prompts",
            "nbr12721.extraction.serialization",
            "nbr12721.extraction.validation",
            "nbr12721.extraction.field_responsibility",
            "nbr12721.integrations",
            "nbr12721.integrations.cub",
            "nbr12721.integrations.llm",
            "nbr12721.orchestration",
            "nbr12721.orchestration.pipeline",
            "nbr12721.orchestration.pipeline_llm",
            "nbr12721.orchestration.pipeline_modes",
            "nbr12721.orchestration.pipeline_postprocess",
            "nbr12721.outputs",
            "nbr12721.outputs.excel_writer",
            "nbr12721.outputs.formatacao",
            "nbr12721.settings",
            "nbr12721.settings.config",
            "nbr12721.settings.logging_setup",
            "nbr12721",
        ]
        for nome in modulos:
            with self.subTest(modulo=nome):
                __import__(nome)

    def test_validation_exporta_validar(self):
        from nbr12721.extraction import validation

        self.assertEqual(validation.__all__, ["validar_dados_extraidos"])
        self.assertTrue(callable(validation.validar_dados_extraidos))

    def test_llm_exporta_chamar_llm(self):
        from nbr12721.integrations import llm
        self.assertIn("chamar_llm", llm.__all__)
        self.assertTrue(inspect.iscoroutinefunction(llm.chamar_llm))

    def test_config_exporta_resolvers_llm(self):
        from nbr12721.settings import config
        for nome in (
            "resolver_llm_provider",
            "resolver_llm_auto_primary",
            "resolver_openai_model",
        ):
            with self.subTest(resolver=nome):
                self.assertTrue(callable(getattr(config, nome)))

    def test_config_paths_padrao(self):
        from nbr12721.settings.config import PASTA_DOCS, PASTA_SAIDA, PLANILHA
        docs = PASTA_DOCS.replace("\\", "/")
        saida = PASTA_SAIDA.replace("\\", "/")
        planilha = PLANILHA.replace("\\", "/")
        self.assertTrue(docs.endswith("data/input/documentos"))
        self.assertTrue(saida.endswith("data/output/saida"))
        self.assertTrue(planilha.endswith("assets/ABNT_NBR_12721-2006.xlsx"))

    def test_config_ocr_padrao(self):
        from nbr12721.settings.config import (
            OCR_DPI,
            OCR_GRAYSCALE,
            OCR_MAX_IMAGE_PIXELS,
            OCR_MIN_CHARS_PAGINA,
            OCR_TIMEOUT_SEGUNDOS,
            OCR_USAR_ARQUIVOS_TEMP,
        )
        self.assertGreater(OCR_DPI, 0)
        self.assertGreater(OCR_MIN_CHARS_PAGINA, 0)
        self.assertGreater(OCR_TIMEOUT_SEGUNDOS, 0)
        self.assertGreater(OCR_MAX_IMAGE_PIXELS, 0)
        self.assertIsInstance(OCR_USAR_ARQUIVOS_TEMP, bool)
        self.assertIsInstance(OCR_GRAYSCALE, bool)


if __name__ == "__main__":
    unittest.main()
