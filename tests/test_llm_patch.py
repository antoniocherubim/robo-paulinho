import copy
import unittest

from nbr12721.extraction.llm_patch import (
    aplicar_patch_llm,
    filtrar_patch_permitido,
    validar_item_patch,
)


def _item(path: str, valor, evidencia: str = "trecho do documento", confianca: str = "alta"):
    return {
        "path": path,
        "valor": valor,
        "evidencia": evidencia,
        "confianca": confianca,
    }


class TestLlmPatch(unittest.TestCase):
    def test_rejeita_path_nao_permitido(self):
        ok, motivo = validar_item_patch(
            _item("projeto.qtdUnidades", 999, "evidencia qualquer")
        )
        self.assertFalse(ok)
        self.assertIn("nao permitido", motivo)

        permitidos, rejeitados = filtrar_patch_permitido(
            [_item("projeto.qtdUnidades", 999)]
        )
        self.assertEqual(permitidos, [])
        self.assertEqual(len(rejeitados), 1)

    def test_aplica_nome_edificio_quando_lixo_ocr(self):
        dados = {"projeto": {"nomeEdificio": ", RESIDENCIAL [memorial.pdf]"}}
        patch = [_item("projeto.nomeEdificio", "Residencial Alpha")]
        resultado = aplicar_patch_llm(dados, patch)
        self.assertEqual(resultado["projeto"]["nomeEdificio"], "Residencial Alpha")
        self.assertIn("_patch_llm_aplicado", resultado)

    def test_nao_aplica_local_construcao_quando_bom(self):
        dados = {"projeto": {"localConstrucao": "Lote 22, Bairro Centro"}}
        patch = [_item("projeto.localConstrucao", "Outro endereco")]
        resultado = aplicar_patch_llm(dados, patch)
        self.assertEqual(resultado["projeto"]["localConstrucao"], "Lote 22, Bairro Centro")
        rejeitados = resultado.get("_patch_llm_rejeitado", [])
        self.assertTrue(any(r.get("path") == "projeto.localConstrucao" for r in rejeitados))

    def test_aplica_quadro6_lista_nao_vazia(self):
        dados = {"quadro6": {"equipamentos": []}}
        patch = [
            _item(
                "quadro6.equipamentos",
                [{"nome": "Elevador", "tipo": "Social", "acabamento": "", "detalhes": ""}],
            )
        ]
        resultado = aplicar_patch_llm(dados, patch)
        self.assertEqual(len(resultado["quadro6"]["equipamentos"]), 1)
        self.assertEqual(resultado["quadro6"]["equipamentos"][0]["nome"], "Elevador")

    def test_rejeita_quadro7_template_vazio(self):
        ok, motivo = validar_item_patch(
            _item(
                "quadro7.acabamentos",
                [{"dependencia": "", "pisos": "", "paredes": "", "tetos": "", "outros": ""}],
            )
        )
        self.assertFalse(ok)
        self.assertIn("lista vazia", motivo)

    def test_nao_muta_original(self):
        dados = {"projeto": {"nomeEdificio": ""}}
        original = copy.deepcopy(dados)
        aplicar_patch_llm(dados, [_item("projeto.nomeEdificio", "Novo Nome")])
        self.assertEqual(dados, original)

    def test_registra_patch_aplicado(self):
        dados = {"incorporador": {"nome": ""}}
        patch = [_item("incorporador.nome", "ACME LTDA")]
        resultado = aplicar_patch_llm(dados, patch)
        aplicados = resultado.get("_patch_llm_aplicado", [])
        self.assertEqual(len(aplicados), 1)
        self.assertEqual(aplicados[0]["path"], "incorporador.nome")
        self.assertEqual(aplicados[0]["confianca"], "alta")


if __name__ == "__main__":
    unittest.main()
