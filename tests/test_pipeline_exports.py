import inspect
import unittest

from nbr12721.main import main
from nbr12721.orchestration.pipeline import executar_pipeline
from nbr12721.orchestration.pipeline_llm import extrair_evidencias_criticas


class TestPipelineExports(unittest.TestCase):
    def test_executar_pipeline_e_coroutine(self):
        self.assertTrue(inspect.iscoroutinefunction(executar_pipeline))

    def test_main_e_funcao(self):
        self.assertTrue(callable(main))

    def test_extrai_multiplas_secoes_de_evidencias(self):
        textos = (
            "EVIDENCIAS CRITICAS EXTRAIDAS DO TEXTO ORIGINAL:\n"
            "A\n\nTEXTO FILTRADO COMPLEMENTAR:\nfoo\n\n"
            "EVIDENCIAS CRITICAS EXTRAIDAS DO TEXTO ORIGINAL:\n"
            "B\n\nTEXTO FILTRADO COMPLEMENTAR:\nbar"
        )
        evidencias = extrair_evidencias_criticas(textos)
        self.assertIn("A", evidencias)
        self.assertIn("B", evidencias)


if __name__ == "__main__":
    unittest.main()
