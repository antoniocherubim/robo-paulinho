import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from nbr12721.settings.config import VALIDACAO_BLOQUEANTE
from nbr12721.orchestration.pipeline_llm import extrair_dados_via_llm
from nbr12721.orchestration.pipeline_modes import (
    somente_json,
    usar_extracao_deterministica,
    usar_fallback_llm,
)
from nbr12721.orchestration.pipeline_postprocess import (
    preencher_derivados_seguros,
    preencher_cub_automatico,
    registrar_validacao_dados,
)


def _dados_minimos_validos() -> dict:
    return {
        "incorporador": {
            "nome": "ACME INCORPORAÇÃO LTDA",
            "cnpj": "12.345.678/0001-90",
            "endereco": "",
        },
        "responsavel": {
            "nome": "MARIA DE SOUZA PEREIRA",
            "crea": "",
            "art": "",
            "endereco": "",
        },
        "projeto": {
            "nomeEdificio": "RESIDENCIAL ALPHA",
            "localConstrucao": "LOTE 22, BAIRRO CENTRO",
            "cidadeUf": "Curitiba-PR",
            "projetoPadrao": {
                "R": True,
                "CS": False,
                "CL": False,
                "CG": False,
                "CP": False,
                "CP1Q": False,
            },
            "qtdUnidades": 320,
            "numPavimentos": 22,
            "vagasUA": 0,
            "vagasAcessorio": 21,
            "vagasComum": 55,
            "areaTerreno": 8958.97,
            "dataAprovacao": "",
            "numAlvara": "2457/2023",
        },
        "quadro1": {
            "pavimentos": [
                {
                    "nome": "Pavimentos tipo",
                    "areaPrivCobPadrao": 20242.0,
                    "qtdPavimentos": 20,
                }
            ],
        },
        "quadro2": {
            "unidades": [
                {
                    "designacao": "Apartamento tipo 66,02 m²",
                    "areaPrivCobPadrao": 66.02,
                    "qtdUnidades": 160,
                }
            ],
        },
        "quadro3": {"valorCub": 2500.55},
        "quadro5": {
            "tipoEdificacao": "EDIFICACAO RESIDENCIAL",
            "garagens": "55 vagas comuns",
        },
    }


class TestPipelineModes(unittest.TestCase):
    def test_usar_extracao_deterministica_por_flag(self):
        with patch("nbr12721.orchestration.pipeline_modes.EXTRACAO_DETERMINISTICA", False):
            self.assertTrue(
                usar_extracao_deterministica(["prog", "--deterministico"])
            )
            self.assertFalse(usar_extracao_deterministica(["prog"]))

    def test_somente_json_por_flag(self):
        self.assertTrue(somente_json(["prog", "--json-only"]))
        self.assertFalse(somente_json(["prog"]))

    def test_preencher_cub_automatico_residencial(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}, "numPavimentos": 3},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "sindicato": "",
                "mesCub": "",
                "valorCub": 0,
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {"R4-N": 2500.55, "R1-N": 2300.10},
        }
        preencher_cub_automatico(dados, cub_info)
        self.assertEqual(dados["quadro3"]["valorCub"], 2300.10)
        self.assertEqual(dados["quadro3"]["sindicato"], "SINDUSCON NORTE PR")
        self.assertEqual(dados["quadro3"]["mesCub"], "Abril/2026")

    def test_preencher_cub_nao_preenche_sem_num_pavimentos(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}, "numPavimentos": 0},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "sindicato": "",
                "mesCub": "",
                "valorCub": 0,
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {"R1-N": 3143.09, "R16-N": 2492.09},
        }
        preencher_cub_automatico(dados, cub_info)
        self.assertEqual(dados["quadro3"]["valorCub"], 0)

    def test_preencher_cub_residencial_21_pavimentos_r16(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}, "numPavimentos": 21},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "sindicato": "",
                "mesCub": "",
                "valorCub": 0,
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {
                "R16-N": 2492.09,
                "R8-N": 2568.85,
                "R1-N": 3143.09,
            },
        }
        preencher_cub_automatico(dados, cub_info)
        self.assertAlmostEqual(dados["quadro3"]["valorCub"], 2492.09)

    def test_preencher_cub_nao_sobrescreve_valor_existente(self):
        dados = {
            "projeto": {"projetoPadrao": {"R": True}},
            "quadro3": {
                "projetoPadrao": {"padrao": ""},
                "valorCub": 999,
                "sindicato": "",
                "mesCub": "",
            },
        }
        cub_info = {
            "sindicato": "SINDUSCON NORTE PR",
            "mesAno": "Abril/2026",
            "valores": {"R4-N": 2500.55},
        }
        preencher_cub_automatico(dados, cub_info)
        self.assertEqual(dados["quadro3"]["valorCub"], 999)

    def test_preencher_derivados_seguros_garagens(self):
        dados = {
            "projeto": {"vagasComum": 72, "vagasAcessorio": "50"},
            "quadro5": {"garagens": ""},
        }
        preencher_derivados_seguros(dados)
        self.assertEqual(dados["quadro5"]["garagens"], "72 vagas comuns; 50 vagas duplas")

    def test_registrar_validacao_dados_salva_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("nbr12721.orchestration.pipeline_postprocess.PASTA_SAIDA", tmpdir),
                patch(
                    "nbr12721.orchestration.pipeline_postprocess.caminho_saida",
                    lambda nome: os.path.join(tmpdir, nome),
                ),
            ):
                resultado = registrar_validacao_dados({})

            self.assertFalse(resultado["ok"])
            path_json = os.path.join(tmpdir, "validacao_dados.json")
            self.assertTrue(os.path.exists(path_json))
            with open(path_json, encoding="utf-8") as f:
                salvo = json.load(f)
            self.assertEqual(salvo["score"], resultado["score"])
            self.assertIn("incorporador.cnpj", salvo["criticos_faltantes"])

    def test_registrar_validacao_dados_retorna_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("nbr12721.orchestration.pipeline_postprocess.PASTA_SAIDA", tmpdir),
                patch(
                    "nbr12721.orchestration.pipeline_postprocess.caminho_saida",
                    lambda nome: os.path.join(tmpdir, nome),
                ),
            ):
                resultado = registrar_validacao_dados(_dados_minimos_validos())

            self.assertTrue(resultado["ok"])

    def test_config_validacao_bloqueante_default_bool(self):
        self.assertIsInstance(VALIDACAO_BLOQUEANTE, bool)

    def test_usar_fallback_llm_por_flag(self):
        with patch("nbr12721.orchestration.pipeline_modes.FALLBACK_LLM_SE_INVALIDO", False):
            self.assertTrue(usar_fallback_llm(["prog", "--fallback-llm"]))
            self.assertFalse(usar_fallback_llm(["prog"]))

    def test_usar_fallback_llm_por_constante(self):
        with patch("nbr12721.orchestration.pipeline_modes.FALLBACK_LLM_SE_INVALIDO", True):
            self.assertTrue(usar_fallback_llm(["prog"]))

    def test_extrair_dados_via_llm_parseia_json(self):
        json_llm = '{"incorporador":{"cnpj":"10.910.748/0001-85"}}'
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("nbr12721.orchestration.pipeline_llm.PASTA_SAIDA", tmpdir),
                patch(
                    "nbr12721.orchestration.pipeline_llm.caminho_saida",
                    lambda nome: os.path.join(tmpdir, nome),
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm._resumir_lotes_documentos",
                    new_callable=AsyncMock,
                    return_value=[{}],
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.compactar_resumos",
                    return_value="RESUMO",
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.extrair_evidencias_criticas",
                    return_value="",
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.chamar_llm",
                    new_callable=AsyncMock,
                    return_value=json_llm,
                ),
            ):
                dados = asyncio.run(extrair_dados_via_llm("texto", None))

        self.assertEqual(dados["incorporador"]["cnpj"], "10.910.748/0001-85")

    def test_extrair_dados_via_llm_falha_sem_resposta(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                patch("nbr12721.orchestration.pipeline_llm.PASTA_SAIDA", tmpdir),
                patch(
                    "nbr12721.orchestration.pipeline_llm.caminho_saida",
                    lambda nome: os.path.join(tmpdir, nome),
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm._resumir_lotes_documentos",
                    new_callable=AsyncMock,
                    return_value=[{}],
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.compactar_resumos",
                    return_value="RESUMO",
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.extrair_evidencias_criticas",
                    return_value="",
                ),
                patch(
                    "nbr12721.orchestration.pipeline_llm.chamar_llm",
                    new_callable=AsyncMock,
                    return_value=None,
                ),
            ):
                with self.assertRaises(RuntimeError):
                    asyncio.run(extrair_dados_via_llm("texto", None))


if __name__ == "__main__":
    unittest.main()
