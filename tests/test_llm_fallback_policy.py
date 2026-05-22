import os
import unittest
from unittest import mock

from nbr12721.llm import (
    chamar_llm,
    _cadeia_anthropic,
    _PROVIDER_ANTHROPIC,
    _PROVIDER_OPENAI,
)


class TestOpenaiEstrito(unittest.IsolatedAsyncioTestCase):
    async def test_falha_openai_nao_chama_anthropic(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
            with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    mock_openai.return_value = None
                    resultado = await chamar_llm("prompt")

        self.assertIsNone(resultado)
        mock_openai.assert_awaited_once()
        mock_anthropic.assert_not_awaited()


class TestCadeiaAnthropicInterna(unittest.IsolatedAsyncioTestCase):
    async def test_api_falha_sdk_responde(self):
        with mock.patch("nbr12721.llm._anthropic_api_disponivel", return_value=True):
            with mock.patch("nbr12721.llm.chamar_claude_api", new_callable=mock.AsyncMock) as mock_api:
                with mock.patch("nbr12721.llm._anthropic_agent_sdk_disponivel", return_value=True):
                    with mock.patch("nbr12721.llm.chamar_claude_sdk", new_callable=mock.AsyncMock) as mock_sdk:
                        mock_api.return_value = None
                        mock_sdk.return_value = '{"via": "sdk"}'
                        resultado = await _cadeia_anthropic("prompt")

        mock_api.assert_awaited_once()
        mock_sdk.assert_awaited_once()
        self.assertEqual(resultado, '{"via": "sdk"}')

    async def test_todos_mecanismos_falham(self):
        with mock.patch("nbr12721.llm._anthropic_api_disponivel", return_value=False):
            with mock.patch("nbr12721.llm._anthropic_agent_sdk_disponivel", return_value=False):
                with mock.patch("nbr12721.llm._executar_claude_cli", return_value=None):
                    resultado = await _cadeia_anthropic("prompt")

        self.assertIsNone(resultado)


class TestAutoUtilizabilidade(unittest.IsolatedAsyncioTestCase):
    async def test_nenhum_provider_utilizavel(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "auto"}):
            with mock.patch("nbr12721.llm._provider_utilizavel", return_value=False):
                with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        resultado = await chamar_llm("prompt")

        self.assertIsNone(resultado)
        mock_anthropic.assert_not_awaited()
        mock_openai.assert_not_awaited()

    async def test_somente_openai_utilizavel(self):
        def utilizavel(provider):
            return provider == _PROVIDER_OPENAI

        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "anthropic"}):
            with mock.patch("nbr12721.llm._provider_utilizavel", side_effect=utilizavel):
                with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_openai.return_value = "ok-openai"
                        resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, "ok-openai")
        mock_anthropic.assert_not_awaited()
        mock_openai.assert_awaited_once()

    async def test_somente_anthropic_utilizavel(self):
        def utilizavel(provider):
            return provider == _PROVIDER_ANTHROPIC

        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "openai"}):
            with mock.patch("nbr12721.llm._provider_utilizavel", side_effect=utilizavel):
                with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_anthropic.return_value = "ok-anthropic"
                        resultado = await chamar_llm("prompt")

        self.assertEqual(resultado, "ok-anthropic")
        mock_openai.assert_not_awaited()
        mock_anthropic.assert_awaited_once()


class TestAutoLogsFallback(unittest.IsolatedAsyncioTestCase):
    async def test_log_tentando_secundario_e_falha_total(self):
        with mock.patch.dict(
            os.environ,
            {"LLM_PROVIDER": "auto", "LLM_AUTO_PRIMARY": "anthropic"},
        ):
            with mock.patch("nbr12721.llm._provider_utilizavel", return_value=True):
                with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_anthropic:
                    with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_openai:
                        mock_anthropic.return_value = None
                        mock_openai.return_value = None
                        with self.assertLogs("nbr12721.llm", level="WARNING") as log_ctx:
                            resultado = await chamar_llm("prompt")

        self.assertIsNone(resultado)
        mensagens = " ".join(log_ctx.output)
        self.assertIn("sem resposta, tentando openai", mensagens)
        self.assertIn("nenhum provider retornou resposta (modo auto)", mensagens)


if __name__ == "__main__":
    unittest.main()
