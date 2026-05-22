# Testes

Suite determinística, **sem rede** e sem chamadas reais a LLM.

## Executar

```bash
./run_tests.sh
# ou: PYTHONPATH=src python3 -m unittest discover -s tests -v
# ou, apos pip install -e . na raiz do projeto:
python3 -m unittest discover -s tests -v
```

`tests/__init__.py` e `conftest.py` adicionam `src/` ao `PYTHONPATH`.

## Cobertura da arquitetura LLM multi-provider

| Arquivo | Escopo |
|---------|--------|
| `test_imports.py` | Import de módulos; `chamar_llm` e resolvers em `config` |
| `test_llm_provider_config.py` | `LLM_PROVIDER`, `LLM_AUTO_PRIMARY`, `OPENAI_MODEL` via env |
| `test_llm_disponibilidade.py` | Utilizabilidade de providers; `_ordenar_providers_auto`; `_executar_provider` |
| `test_chamar_llm_routing.py` | Roteamento de `chamar_llm` (anthropic / openai / auto / ordem) |
| `test_llm_fallback_policy.py` | Fallback estrito, cadeia interna Anthropic, auto sem providers |
| `test_llm_response_contract.py` | Normalização de texto e adaptadores de resposta |
| `test_openai_api.py` | `chamar_openai_api` com mock (retry 429, auth, sucesso) |

## Outros módulos

| Arquivo | Escopo |
|---------|--------|
| `test_serialization.py` | `parsear_json`, `compactar_resumos` |
| `test_formatacao.py` | `formatar_brl` |
| `test_pipeline_exports.py` | `executar_pipeline` é coroutine |

## Princípios

- `unittest.mock` para env (`patch.dict(os.environ)`) e clientes API.
- Pacote `openai` mockado via `sys.modules` quando não instalado.
- Nenhum teste depende de `ANTHROPIC_API_KEY` ou `OPENAI_API_KEY` reais.
