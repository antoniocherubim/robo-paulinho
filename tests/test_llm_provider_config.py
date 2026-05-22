import os
import unittest
from unittest import mock

from nbr12721.config import (
    resolver_llm_provider,
    resolver_llm_auto_primary,
    resolver_openai_model,
    LLM_PROVIDER_PADRAO,
    LLM_AUTO_PRIMARY_PADRAO,
    LLM_PROVIDER_VALIDOS,
    MODELO_OPENAI_PADRAO,
)


class TestResolverLlmProvider(unittest.TestCase):
    def test_ausente_retorna_anthropic(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_PROVIDER", None)
            self.assertEqual(resolver_llm_provider(), LLM_PROVIDER_PADRAO)

    def test_anthropic_explicito(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}):
            self.assertEqual(resolver_llm_provider(), "anthropic")

    def test_normaliza_maiusculas(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "  AUTO  "}):
            self.assertEqual(resolver_llm_provider(), "auto")

    def test_invalido_fallback_anthropic(self):
        with mock.patch.dict(os.environ, {"LLM_PROVIDER": "gemini"}):
            self.assertEqual(resolver_llm_provider(), LLM_PROVIDER_PADRAO)

    def test_todos_valores_validos(self):
        for valor in LLM_PROVIDER_VALIDOS:
            with self.subTest(valor=valor):
                with mock.patch.dict(os.environ, {"LLM_PROVIDER": valor}):
                    self.assertEqual(resolver_llm_provider(), valor)


class TestResolverOpenaiModel(unittest.TestCase):
    def test_default_gpt4o(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_MODEL", None)
            self.assertEqual(resolver_openai_model(), MODELO_OPENAI_PADRAO)
            self.assertEqual(MODELO_OPENAI_PADRAO, "gpt-4o")

    def test_override_env(self):
        with mock.patch.dict(os.environ, {"OPENAI_MODEL": "gpt-5"}):
            self.assertEqual(resolver_openai_model(), "gpt-5")


class TestResolverLlmAutoPrimary(unittest.TestCase):
    def test_ausente_retorna_anthropic(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_AUTO_PRIMARY", None)
            self.assertEqual(resolver_llm_auto_primary(), LLM_AUTO_PRIMARY_PADRAO)

    def test_openai_explicito(self):
        with mock.patch.dict(os.environ, {"LLM_AUTO_PRIMARY": "openai"}):
            self.assertEqual(resolver_llm_auto_primary(), "openai")

    def test_invalido_fallback_anthropic(self):
        with mock.patch.dict(os.environ, {"LLM_AUTO_PRIMARY": "azure"}):
            self.assertEqual(resolver_llm_auto_primary(), LLM_AUTO_PRIMARY_PADRAO)


if __name__ == "__main__":
    unittest.main()
