import unittest

from nbr12721.integrations.llm import (
    _normalizar_texto_resposta,
    _classificar_erro,
    _texto_de_resposta_anthropic_api,
    _texto_de_resposta_anthropic_sdk,
    _texto_de_resposta_openai_api,
)


class TestNormalizarTextoResposta(unittest.TestCase):
    def test_none(self):
        self.assertIsNone(_normalizar_texto_resposta(None))

    def test_vazio_e_whitespace(self):
        self.assertIsNone(_normalizar_texto_resposta(""))
        self.assertIsNone(_normalizar_texto_resposta("  \n\t  "))

    def test_strip_preserva_conteudo(self):
        self.assertEqual(_normalizar_texto_resposta('  {"a": 1}  '), '{"a": 1}')

    def test_crlf_para_lf(self):
        self.assertEqual(_normalizar_texto_resposta("a\r\nb"), "a\nb")

    def test_fence_markdown_nao_removida(self):
        entrada = '  \n```json\n{"ok": true}\n```\n  '
        esperado = '```json\n{"ok": true}\n```'
        self.assertEqual(_normalizar_texto_resposta(entrada), esperado)

    def test_tipo_invalido(self):
        self.assertIsNone(_normalizar_texto_resposta(42))


class TestClassificarErro(unittest.TestCase):
    def test_rate_limit_recuperavel(self):
        recuperavel, _ = _classificar_erro(Exception("Error 429 rate limit"))
        self.assertTrue(recuperavel)

    def test_auth_nao_recuperavel(self):
        recuperavel, msg = _classificar_erro(Exception("401 invalid_api_key"))
        self.assertFalse(recuperavel)
        self.assertIn("autenticacao", msg)

    def test_import_error(self):
        recuperavel, msg = _classificar_erro(ImportError("no module anthropic"))
        self.assertFalse(recuperavel)
        self.assertIn("dependencia", msg)


class TestAdaptadores(unittest.TestCase):
    def test_anthropic_api_blocos_texto(self):
        class Bloco:
            def __init__(self, text):
                self.text = text

        class Resp:
            content = [Bloco('{"x":'), Bloco("1}")]

        self.assertEqual(_texto_de_resposta_anthropic_api(Resp()), '{"x":1}')

    def test_anthropic_sdk(self):
        self.assertEqual(_texto_de_resposta_anthropic_sdk("  ok  "), "ok")

    def test_openai_api_stub_none(self):
        self.assertIsNone(_texto_de_resposta_openai_api(None))

    def test_openai_api_string_content(self):
        class Message:
            content = '{"a": 1}'

        class Choice:
            message = Message()

        class Resp:
            choices = [Choice()]

        self.assertEqual(_texto_de_resposta_openai_api(Resp()), '{"a": 1}')

    def test_openai_api_choices_vazio(self):
        class Resp:
            choices = []

        self.assertIsNone(_texto_de_resposta_openai_api(Resp()))

    def test_openai_api_content_ausente(self):
        class Message:
            pass

        class Choice:
            message = Message()

        class Resp:
            choices = [Choice()]

        self.assertIsNone(_texto_de_resposta_openai_api(Resp()))


if __name__ == "__main__":
    unittest.main()
