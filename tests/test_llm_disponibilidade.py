import os
import unittest
from unittest import mock

from nbr12721.llm import (
    _anthropic_api_disponivel,
    _anthropic_provider_utilizavel,
    _openai_provider_utilizavel,
    _provider_utilizavel,
    _ordenar_providers_auto,
    _executar_provider,
    _PROVIDER_ANTHROPIC,
    _PROVIDER_OPENAI,
)


class TestDisponibilidadeEnv(unittest.TestCase):
    def test_anthropic_api_com_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant"}):
            self.assertTrue(_anthropic_api_disponivel())

    def test_anthropic_api_sem_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertFalse(_anthropic_api_disponivel())

    def test_openai_com_key(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-openai"}):
            self.assertTrue(_openai_provider_utilizavel())

    def test_openai_sem_key(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            self.assertFalse(_openai_provider_utilizavel())


class TestProviderUtilizavel(unittest.TestCase):
    def test_anthropic_utilizavel_via_api(self):
        with mock.patch("nbr12721.llm._anthropic_api_disponivel", return_value=True):
            with mock.patch("nbr12721.llm._anthropic_agent_sdk_disponivel", return_value=False):
                with mock.patch("nbr12721.llm._encontrar_claude", return_value=None):
                    self.assertTrue(_anthropic_provider_utilizavel())

    def test_anthropic_utilizavel_via_cli(self):
        with mock.patch("nbr12721.llm._anthropic_api_disponivel", return_value=False):
            with mock.patch("nbr12721.llm._anthropic_agent_sdk_disponivel", return_value=False):
                with mock.patch("nbr12721.llm._encontrar_claude", return_value="/usr/bin/claude"):
                    self.assertTrue(_anthropic_provider_utilizavel())

    def test_anthropic_nao_utilizavel(self):
        with mock.patch("nbr12721.llm._anthropic_api_disponivel", return_value=False):
            with mock.patch("nbr12721.llm._anthropic_agent_sdk_disponivel", return_value=False):
                with mock.patch("nbr12721.llm._encontrar_claude", return_value=None):
                    self.assertFalse(_anthropic_provider_utilizavel())

    def test_provider_utilizavel_dispatch(self):
        with mock.patch("nbr12721.llm._anthropic_provider_utilizavel", return_value=True):
            with mock.patch("nbr12721.llm._openai_provider_utilizavel", return_value=False):
                self.assertTrue(_provider_utilizavel(_PROVIDER_ANTHROPIC))
                self.assertFalse(_provider_utilizavel(_PROVIDER_OPENAI))


class TestOrdenarProvidersAuto(unittest.TestCase):
    def test_primario_anthropic(self):
        with mock.patch.dict(os.environ, {"LLM_AUTO_PRIMARY": "anthropic"}):
            primario, secundario = _ordenar_providers_auto()
        self.assertEqual(primario, _PROVIDER_ANTHROPIC)
        self.assertEqual(secundario, _PROVIDER_OPENAI)

    def test_primario_openai(self):
        with mock.patch.dict(os.environ, {"LLM_AUTO_PRIMARY": "openai"}):
            primario, secundario = _ordenar_providers_auto()
        self.assertEqual(primario, _PROVIDER_OPENAI)
        self.assertEqual(secundario, _PROVIDER_ANTHROPIC)


class TestExecutarProvider(unittest.IsolatedAsyncioTestCase):
    async def test_executar_anthropic(self):
        with mock.patch("nbr12721.llm._cadeia_anthropic", new_callable=mock.AsyncMock) as mock_cadeia:
            mock_cadeia.return_value = "texto"
            resultado = await _executar_provider(_PROVIDER_ANTHROPIC, "p", "sys")
        mock_cadeia.assert_awaited_once()
        self.assertEqual(resultado, "texto")

    async def test_executar_openai(self):
        with mock.patch("nbr12721.llm._cadeia_openai", new_callable=mock.AsyncMock) as mock_cadeia:
            mock_cadeia.return_value = "texto"
            resultado = await _executar_provider(_PROVIDER_OPENAI, "p", "sys")
        mock_cadeia.assert_awaited_once()
        self.assertEqual(resultado, "texto")

    async def test_provider_desconhecido(self):
        self.assertIsNone(await _executar_provider("gemini", "p", "sys"))


if __name__ == "__main__":
    unittest.main()
