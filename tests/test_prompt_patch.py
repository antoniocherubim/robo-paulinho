import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from nbr12721.documents.pdf_processing import (
    MARCADOR_EVIDENCIAS_VI_VIII,
    MARCADOR_QUADRO_VI,
    MARCADOR_QUADRO_VII,
    MARCADOR_QUADRO_VIII,
)
from nbr12721.extraction.prompts import PROMPT_ENRIQUECER_PATCH
from nbr12721.orchestration.pipeline_llm import (
    _anexar_evidencias_patch,
    _truncar_bloco_vi_viii,
    gerar_patch_llm,
)
from nbr12721.settings.config import LIMITE_CHARS_PROMPT_FINAL


class TestPromptPatch(unittest.TestCase):
    def test_prompt_proibe_lista_vazia_e_template_vazio(self):
        self.assertIn("Lista vazia e proibida", PROMPT_ENRIQUECER_PATCH)
        self.assertIn("template vazio", PROMPT_ENRIQUECER_PATCH)
        self.assertIn("quadro6.equipamentos", PROMPT_ENRIQUECER_PATCH)
        self.assertIn("quadro7.acabamentos", PROMPT_ENRIQUECER_PATCH)
        self.assertIn("quadro8.acabamentos", PROMPT_ENRIQUECER_PATCH)

    def test_prompt_restringe_quadro7_quadro8_por_secao(self):
        self.assertIn(MARCADOR_QUADRO_VII, PROMPT_ENRIQUECER_PATCH)
        self.assertIn(MARCADOR_QUADRO_VIII, PROMPT_ENRIQUECER_PATCH)
        self.assertIn("SOMENTE", PROMPT_ENRIQUECER_PATCH)
        self.assertIn('"Area"', PROMPT_ENRIQUECER_PATCH)
        self.assertIn("nao_encontrado", PROMPT_ENRIQUECER_PATCH)

    def test_anexar_evidencias_patch_preserva_bloco(self):
        base = "A" * 100
        evidencias = f"{MARCADOR_EVIDENCIAS_VI_VIII}\n[doc.pdf] ELEVADOR01"
        resultado = _anexar_evidencias_patch(base, evidencias, limite_chars=80)
        self.assertIn(MARCADOR_EVIDENCIAS_VI_VIII, resultado)
        self.assertIn("ELEVADOR01", resultado)
        self.assertLessEqual(len(resultado), 80)

    def test_anexar_evidencias_patch_preserva_subsecoes_vi_viii(self):
        bloco = "\n".join(
            [
                MARCADOR_EVIDENCIAS_VI_VIII,
                "",
                MARCADOR_QUADRO_VI,
                "[doc.pdf] ELEVADOR01",
                "",
                MARCADOR_QUADRO_VII,
                "[doc.pdf] APTO01 SALA PISO PORCELANATO",
                "",
                MARCADOR_QUADRO_VIII,
                "[doc.pdf] HALL ELEV. PISO PORCELANATO",
            ]
        )
        resultado = _anexar_evidencias_patch("A" * 500, bloco, limite_chars=200)
        self.assertIn(MARCADOR_EVIDENCIAS_VI_VIII, resultado)
        self.assertIn(MARCADOR_QUADRO_VI, resultado)
        self.assertIn(MARCADOR_QUADRO_VII, resultado)
        self.assertIn(MARCADOR_QUADRO_VIII, resultado)
        self.assertLessEqual(len(resultado), 200)

    def test_truncar_bloco_vi_viii_preserva_cabecalhos_vazios(self):
        bloco = "\n".join(
            [
                MARCADOR_EVIDENCIAS_VI_VIII,
                "",
                MARCADOR_QUADRO_VI,
                "linha " + "X" * 200,
                "",
                MARCADOR_QUADRO_VII,
                "linha " + "Y" * 200,
                "",
                MARCADOR_QUADRO_VIII,
                "linha " + "Z" * 200,
            ]
        )
        resultado = _truncar_bloco_vi_viii(bloco, limite_chars=120)
        self.assertIn(MARCADOR_EVIDENCIAS_VI_VIII, resultado)
        self.assertIn(MARCADOR_QUADRO_VI, resultado)
        self.assertIn(MARCADOR_QUADRO_VII, resultado)
        self.assertIn(MARCADOR_QUADRO_VIII, resultado)
        # Cabecalhos intactos tem prioridade sobre o limite quando o esqueleto o excede.
        esqueleto = _truncar_bloco_vi_viii(
            "\n".join(
                [
                    MARCADOR_EVIDENCIAS_VI_VIII,
                    "",
                    MARCADOR_QUADRO_VI,
                    "",
                    MARCADOR_QUADRO_VII,
                    "",
                    MARCADOR_QUADRO_VIII,
                ]
            ),
            limite_chars=120,
        )
        self.assertEqual(resultado, esqueleto)

        resultado_grande = _truncar_bloco_vi_viii(bloco, limite_chars=500)
        self.assertLessEqual(len(resultado_grande), 500)
        self.assertIn(MARCADOR_QUADRO_VIII, resultado_grande)

    def test_truncar_bloco_vi_viii_remove_vi_antes_de_vii_viii(self):
        bloco = "\n".join(
            [
                MARCADOR_EVIDENCIAS_VI_VIII,
                "",
                MARCADOR_QUADRO_VI,
                "VI-A",
                "VI-B",
                "VI-C",
                "",
                MARCADOR_QUADRO_VII,
                "VII-A",
                "",
                MARCADOR_QUADRO_VIII,
                "VIII-A",
            ]
        )
        esqueleto = _truncar_bloco_vi_viii(
            "\n".join(
                [
                    MARCADOR_EVIDENCIAS_VI_VIII,
                    "",
                    MARCADOR_QUADRO_VI,
                    "",
                    MARCADOR_QUADRO_VII,
                    "",
                    MARCADOR_QUADRO_VIII,
                ]
            ),
            limite_chars=10_000,
        )
        limite = len(esqueleto) + len("VI-A\nVI-B\nVII-A\nVIII-A") + 2
        resultado = _truncar_bloco_vi_viii(bloco, limite_chars=limite)
        self.assertIn("VII-A", resultado)
        self.assertIn("VIII-A", resultado)
        self.assertNotIn("VI-C", resultado)

    def test_anexar_evidencias_patch_sem_evidencias_retorna_base(self):
        base = "texto base"
        self.assertEqual(_anexar_evidencias_patch(base, ""), base)

    def test_anexar_evidencias_patch_respeita_limite_global(self):
        base = "B" * (LIMITE_CHARS_PROMPT_FINAL - 10)
        evidencias = f"{MARCADOR_EVIDENCIAS_VI_VIII}\nlinha"
        resultado = _anexar_evidencias_patch(
            base, evidencias, limite_chars=LIMITE_CHARS_PROMPT_FINAL
        )
        self.assertLessEqual(len(resultado), LIMITE_CHARS_PROMPT_FINAL)
        self.assertTrue(resultado.endswith("linha") or MARCADOR_EVIDENCIAS_VI_VIII in resultado)

    def test_gerar_patch_llm_inclui_evidencias_vi_viii_no_prompt(self):
        evidencias = f"{MARCADOR_EVIDENCIAS_VI_VIII}\n[memorial.pdf] ELEVADOR01"
        prompt_capturado: list[str] = []

        async def _capturar_prompt(prompt: str) -> str:
            prompt_capturado.append(prompt)
            return '{"patch":[],"nao_encontrado":["quadro6.equipamentos"]}'

        with (
            patch(
                "nbr12721.orchestration.pipeline_llm._preparar_texto_para_llm",
                new_callable=AsyncMock,
                return_value="RESUMO",
            ),
            patch(
                "nbr12721.orchestration.pipeline_llm.extrair_evidencias_acabamentos_equipamentos",
                return_value=evidencias,
            ),
            patch(
                "nbr12721.orchestration.pipeline_llm.chamar_llm",
                side_effect=_capturar_prompt,
            ),
        ):
            resultado = asyncio.run(
                gerar_patch_llm({}, "texto", {"avisos_semanticos": []})
            )

        self.assertEqual(resultado["nao_encontrado"], ["quadro6.equipamentos"])
        self.assertEqual(len(prompt_capturado), 1)
        self.assertIn(MARCADOR_EVIDENCIAS_VI_VIII, prompt_capturado[0])
        self.assertIn("ELEVADOR01", prompt_capturado[0])


if __name__ == "__main__":
    unittest.main()
