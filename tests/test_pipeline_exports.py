import inspect
import unittest

from nbr12721.pipeline import executar_pipeline


class TestPipelineExports(unittest.TestCase):
    def test_executar_pipeline_e_coroutine(self):
        self.assertTrue(inspect.iscoroutinefunction(executar_pipeline))


if __name__ == "__main__":
    unittest.main()
