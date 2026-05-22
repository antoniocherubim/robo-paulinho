# Política de Fallback LLM

O que acontece quando um provider ou mecanismo falha. Complementa [llm-provider-strategy.md](llm-provider-strategy.md) (quem escolhe o provider) e [llm-response-contract.md](llm-response-contract.md) (formato da resposta).

## Princípios

- O pipeline recebe apenas `str | None` de `chamar_llm`.
- **Ausência de credencial** e **erro em runtime** levam ao próximo passo da política ou a `None`.
- **Retry de rate limit** existe só dentro de `chamar_claude_api` e `chamar_openai_api`, nunca entre providers.
- Cross-provider (tentar outro provider após falha) ocorre **somente** com `LLM_PROVIDER=auto`.

**Nota:** o rascunho antigo em `tasks feat openAI.txt` sugeria `auto` fixo como OpenAI → Anthropic. O comportamento oficial deste projeto usa **`LLM_AUTO_PRIMARY`** (default `anthropic`).

## Por `LLM_PROVIDER`

### `openai` (estrito)

| Ordem | Mecanismo | Condição para tentar |
|-------|-----------|----------------------|
| 1 | `openai/api` | `OPENAI_API_KEY` presente |

**Não tenta:** Anthropic (API, SDK, CLI).

**Falha final:** `None` + log `! openai/api sem resposta`.

### `anthropic` (default)

| Ordem | Mecanismo | Condição para tentar |
|-------|-----------|----------------------|
| 1 | `anthropic/api` | `ANTHROPIC_API_KEY` presente |
| 2 | `anthropic/agent_sdk` | pacote `claude_agent_sdk` importável |
| 3 | `anthropic/cli` | executável `claude` encontrável |

**Não tenta:** OpenAI.

**Falha de um mecanismo:** log `! anthropic/<mecanismo> ... tentando <próximo>` e próximo mecanismo na tabela.

**Falha final:** `None` (último mecanismo sem texto).

### `auto`

1. Resolve `LLM_AUTO_PRIMARY` → provider primário; o outro é secundário.
2. Para cada provider na ordem `[primário, secundário]`:
   - Se **não utilizável** → log `! provider <x> nao utilizavel, pulando`.
   - Se utilizável → executa **cadeia completa** desse provider (mesmas regras de `openai` ou `anthropic` acima).
   - Se retornar texto → fim.
   - Se falhar → log `! provider <primario> sem resposta, tentando <secundario>` (antes do secundário).
3. Se nenhum provider retornar texto → `None` + log `! LLM: nenhum provider retornou resposta (modo auto)`.

| `LLM_AUTO_PRIMARY` | Sequência (ambos utilizáveis) |
|--------------------|-------------------------------|
| `anthropic` | Anthropic API→SDK→CLI, depois OpenAI API |
| `openai` | OpenAI API, depois Anthropic API→SDK→CLI |

## Utilizabilidade (modo `auto`)

| Provider | Utilizável quando |
|----------|-------------------|
| `openai` | `OPENAI_API_KEY` não vazio |
| `anthropic` | API key **ou** Agent SDK importável **ou** CLI encontrável |

“API disponível” (só key Anthropic) não equivale a “provider utilizável” sozinho — ver [llm-provider-strategy.md](llm-provider-strategy.md).

## Logs padronizados

| Evento | Formato |
|--------|---------|
| Início modo explícito | `> LLM_PROVIDER=anthropic` / `openai` |
| Início auto | `> LLM_PROVIDER=auto [auto_primary=<valor>]` |
| Sucesso | `+ <provider>/<mechanism> OK (N chars)` |
| Falha mecanismo | `! <provider>/<mechanism> falhou (...)` ou `sem resposta, tentando ...` |
| Provider não utilizável | `! provider <x> nao utilizavel, pulando` |
| Fallback entre providers (auto) | `! provider <primario> sem resposta, tentando <secundario>` |
| Falha total auto | `! LLM: nenhum provider retornou resposta (modo auto)` |

## Matriz rápida de falha

| Cenário | Resultado |
|---------|-----------|
| `openai`, sem `OPENAI_API_KEY` | `None` (cadeia não chama API) |
| `openai`, API falha | `None` |
| `openai`, API ok + key Anthropic | `None` (sem cross-provider) |
| `anthropic`, só CLI ok | SDK/API pulados conforme disponibilidade; CLI responde |
| `anthropic`, tudo falha | `None` |
| `auto`, só um utilizável | só esse provider; cadeia interna completa |
| `auto`, nenhum utilizável | `None` sem chamar cadeias |
| `auto`, primário falha, secundário ok | texto do secundário |

## Implementação

| Arquivo | Funções |
|---------|---------|
| `llm.py` | `_cadeia_anthropic`, `_cadeia_openai`, `chamar_llm` (loop auto) |
| `config.py` | `resolver_llm_provider`, `resolver_llm_auto_primary` |

Testes: `tests/test_llm_fallback_policy.py`, `tests/test_chamar_llm_routing.py`.
