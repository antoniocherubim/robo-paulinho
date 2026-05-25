import os
import unittest
from unittest import mock

from nbr12721.integrations.llm import chamar_llm


class TestChamarLlmRouting(unittest.IsolatedAsyncioTestCase):
    async def test_anthropic_chama_somente_cadeia_anthropic(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):
            with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                    mock_anthropic.return_value = '{"ok": true}'
                    resultado = await chamar_llm("prompt")

        mock_anthropic.assert_awaited_once()
        mock_openai.assert_not_awaited()
        self.assertEqual(resultado, '{"ok": true}')

    async def test_openai_chama_somente_cadeia_openai(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                    mock_openai.return_value = '{"ok": true}'
                    resultado = await chamar_llm("prompt")

        mock_openai.assert_awaited_once()
        mock_anthropic.assert_not_awaited()
        self.assertEqual(resultado, '{"ok": true}')

    async def test_normalizacao_final_no_retorno(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):
            with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                mock_anthropic.return_value = ' {"ok": 1} '
                resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, '{"ok": 1}')

    async def test_falha_total_retorna_none(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                mock_openai.return_value = None
                resultado = await chamar_llm("prompt")

        self.assertIsNone(resultado)

    async def test_auto_anthropic_antes_de_openai(self):
        with mock.patch.dict(
            os.environ,
            {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "anthropic"},
        ):
            with mock.patch("nbr12721.integrations.llm._provider_utilizavel", return_value=True):
                with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_anthropic.return_value = "ok"
                        resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, "ok")
        mock_anthropic.assert_awaited_once()
        mock_openai.assert_not_awaited()

    async def test_auto_openai_antes_de_anthropic(self):
        with mock.patch.dict(
            os.environ,
            {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "openai"},
        ):
            with mock.patch("nbr12721.integrations.llm._provider_utilizavel", return_value=True):
                with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_openai.return_value = "ok"
                        resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, "ok")
        mock_openai.assert_awaited_once()
        mock_anthropic.assert_not_awaited()

    async def test_auto_fallback_para_secundario(self):
        with mock.patch.dict(
            os.environ,
            {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "anthropic"},
        ):
            with mock.patch("nbr12721.integrations.llm._provider_utilizavel", return_value=True):
                with mock.patch("nbr12721.integrations.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.integrations.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_anthropic.return_value = None
                        mock_openai.return_value = "fallback"
                        resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, "fallback")
        mock_anthropic.assert_awaited_once()
        mock_openai.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
