import inspect
import unittest

from nbr12721.main import main
from nbr12721.pipeline import executar_pipeline


class TestPipelineExports(unittest.TestCase):
    def test_executar_pipeline_e_coroutine(self):
        self.assertTrue(inspect.iscoroutinefunction(executar_pipeline))

    def test_main_e_funcao(self):
        self.assertTrue(callable(main))


if __name__ == "__main__":
    unittest.main()
