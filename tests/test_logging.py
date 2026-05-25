import logging
import tempfile
import unittest
from unittest.mock import patch

from nbr12721.settings.logging_setup import configurar_logging, reset_logging


class TestLoggingSetup(unittest.TestCase):
    def setUp(self):
        reset_logging()

    def test_cria_arquivo_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            with (
                patch.dict(
                    "os.environ",
                    {"PASTA_LOGS": tmp, "LOG_ARQUIVO": "teste.log", "LOG_LEVEL": "INFO"},
                ),
                patch(
                    "nbr12721.settings.logging_setup.datetime",
                ) as mock_datetime,
            ):
                mock_datetime.now.return_value.strftime.return_value = "20260525_033538"
                caminho = configurar_logging()
            self.assertTrue(caminho.exists())
            self.assertEqual(caminho.name, "teste_20260525_033538.log")

            log = logging.getLogger("nbr12721.teste")
            log.info("mensagem de teste")

            conteudo = caminho.read_text(encoding="utf-8")
            self.assertIn("mensagem de teste", conteudo)
            self.assertIn("nbr12721.teste", conteudo)


if __name__ == "__main__":
    unittest.main()
