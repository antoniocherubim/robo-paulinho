import os
import sys
import unittest
from unittest import mock

def _patch_openai_client(mock_cliente):
    """Mock do pacote openai importado dentro de chamar_openai_api._chamar."""
    modulo_openai = mock.MagicMock()
    modulo_openai.OpenAI.return_value = mock_cliente
    return mock.patch.dict(sys.modules, {"openai": modulo_openai})


class TestChamarOpenaiApi(unittest.IsolatedAsyncioTestCase):
    async def test_sem_api_key_retorna_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            from nbr12721.llm import chamar_openai_api
            self.assertIsNone(await chamar_openai_api("prompt"))

    async def test_resposta_mock_retorna_texto(self):
        class Message:
            content = '{"ok": true}'

        class Choice:
            message = Message()

        class Resp:
            choices = [Choice()]

        mock_cliente = mock.MagicMock()
        mock_cliente.chat.completions.create.return_value = Resp()

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with mock.patch("nbr12721.llm.asyncio.to_thread", side_effect=lambda fn: fn()):
                with _patch_openai_client(mock_cliente):
                    from nbr12721.llm import chamar_openai_api
                    resultado = await chamar_openai_api("prompt")
        self.assertEqual(resultado, '{"ok": true}')

    async def test_erro_401_sem_retry(self):
        mock_cliente = mock.MagicMock()
        mock_cliente.chat.completions.create.side_effect = Exception("401 invalid_api_key")

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with mock.patch("nbr12721.llm.asyncio.to_thread", side_effect=lambda fn: fn()):
                with _patch_openai_client(mock_cliente):
                    from nbr12721.llm import chamar_openai_api
                    resultado = await chamar_openai_api("prompt")
        self.assertIsNone(resultado)
        self.assertEqual(mock_cliente.chat.completions.create.call_count, 1)

    async def test_erro_429_com_retry(self):
        mock_cliente = mock.MagicMock()
        mock_cliente.chat.completions.create.side_effect = Exception("429 rate limit")

        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            with mock.patch("nbr12721.llm.asyncio.to_thread", side_effect=lambda fn: fn()):
                with _patch_openai_client(mock_cliente):
                    with mock.patch("nbr12721.llm.time.sleep"):
                        with mock.patch("nbr12721.llm.API_MAX_TENTATIVAS", 3):
                            from nbr12721.llm import chamar_openai_api
                            resultado = await chamar_openai_api("prompt")
        self.assertIsNone(resultado)
        self.assertEqual(mock_cliente.chat.completions.create.call_count, 3)


class TestTextoOpenaiApiEdgeCases(unittest.TestCase):
    def test_choices_vazio(self):
        from nbr12721.llm import _texto_de_resposta_openai_api

        class Resp:
            choices = []

        self.assertIsNone(_texto_de_resposta_openai_api(Resp()))

    def test_content_ausente(self):
        from nbr12721.llm import _texto_de_resposta_openai_api

        class Message:
            pass

        class Choice:
            message = Message()

        class Resp:
            choices = [Choice()]

        self.assertIsNone(_texto_de_resposta_openai_api(Resp()))


if __name__ == "__main__":
    unittest.main()
