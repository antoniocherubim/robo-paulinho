import logging
import os
import tempfile
import unittest

from nbr12721.logging_setup import configurar_logging, reset_logging


class TestLoggingSetup(unittest.TestCase):
    def setUp(self):
        reset_logging()

    def test_cria_arquivo_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["PASTA_LOGS"] = tmp
            os.environ["LOG_ARQUIVO"] = "teste.log"
            caminho = configurar_logging()
            self.assertTrue(caminho.exists())
            self.assertEqual(caminho.name, "teste.log")

            log = logging.getLogger("nbr12721.teste")
            log.info("mensagem de teste")

            conteudo = caminho.read_text(encoding="utf-8")
            self.assertIn("mensagem de teste", conteudo)
            self.assertIn("nbr12721.teste", conteudo)


if __name__ == "__main__":
    unittest.main()
