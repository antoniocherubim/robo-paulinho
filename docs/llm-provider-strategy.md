# Estratégia de Provider LLM

Contrato de seleção entre Anthropic e OpenAI para o pipeline NBR 12721. O pipeline chama apenas `chamar_llm(...)` e permanece agnóstico ao provider.

Política de fallback (falhas e ordem de tentativas): [llm-fallback-policy.md](llm-fallback-policy.md).

## Resumo

| `LLM_PROVIDER` | Comportamento |
|----------------|---------------|
| (ausente) ou `anthropic` | Cadeia Anthropic: API → Agent SDK → CLI |
| `openai` | OpenAI API apenas; sem fallback para Anthropic |
| `auto` | Provider primário completo (`LLM_AUTO_PRIMARY`), depois secundário se disponível |

Assinatura pública inalterada: `async def chamar_llm(...) -> str | None`.

## Variáveis de ambiente

| Variável | Valores | Default | Papel |
|----------|---------|---------|-------|
| `LLM_PROVIDER` | `anthropic`, `openai`, `auto` | `anthropic` | Seleção do provider |
| `LLM_AUTO_PRIMARY` | `anthropic`, `openai` | `anthropic` | Ordem em `auto` quando ambos os providers estão utilizáveis |
| `ANTHROPIC_API_KEY` | string | vazio | Credencial da API Anthropic |
| `ANTHROPIC_MODEL` | string | `claude-3-5-sonnet-20241022` | Modelo Anthropic |
| `OPENAI_API_KEY` | string | vazio | Credencial da API OpenAI |
| `OPENAI_MODEL` | string | `gpt-4o` (default do projeto) | Modelo OpenAI — ver seção abaixo |

### Normalização e valores inválidos

- `LLM_PROVIDER` e `LLM_AUTO_PRIMARY`: trim + lowercase antes da validação.
- `LLM_PROVIDER` inválido: aviso no log + fallback para `anthropic`.
- `LLM_AUTO_PRIMARY` inválido: aviso no log + fallback para `anthropic` (simétrico a `LLM_PROVIDER`).

### `OPENAI_MODEL`

**Default do projeto:** `gpt-4o` (`MODELO_OPENAI_PADRAO` em `config.py`), sobrescrevível via `OPENAI_MODEL` no `.env`.

Isso é uma **escolha deste repositório** (compatibilidade/custo e alinhamento com Chat Completions), **não** a recomendação “mais atual” da OpenAI para novas integrações de API.

Referências oficiais:

- [gpt-4o](https://developers.openai.com/api/docs/models/gpt-4o) — modelo válido; documentado como forte opção na família GPT-4o.
- [Models](https://developers.openai.com/api/docs/models) — catálogo geral.
- Orientação mais recente da OpenAI para muitas integrações aponta para modelos GPT-5.x (ex. [chatgpt-4o-latest / família atual](https://developers.openai.com/api/docs/models/chatgpt-4o-latest)).

Para usar um modelo mais novo, defina `OPENAI_MODEL` explicitamente no `.env`.

## Dois níveis: provider vs mecanismo

**Provider** = família de integração (`anthropic`, `openai`).

**Mecanismo** = canal dentro do provider:

| Provider | Mecanismos (ordem) |
|----------|-------------------|
| `anthropic` | `api` → `agent_sdk` → `cli` |
| `openai` | `api` apenas |

SDK e CLI **não** são providers; são fallbacks internos do provider Anthropic.

## Disponibilidade no modo `auto`

Dois conceitos distintos para Anthropic (evita ambiguidade na implementação):

### Nível 1 — API Anthropic disponível

Verdadeiro quando `ANTHROPIC_API_KEY` não está vazio.

- Usado para decidir se o mecanismo `api` pode ser tentado na cadeia Anthropic.
- **Não** equivale a “provider Anthropic utilizável” sozinho.

### Nível 2 — Provider Anthropic utilizável

Verdadeiro quando **pelo menos um** mecanismo pode ser tentado:

- API disponível (`ANTHROPIC_API_KEY`), **ou**
- Agent SDK importável (`claude_agent_sdk`), **ou**
- CLI `claude` encontrável (`_encontrar_claude()`).

Usado em `auto` para incluir Anthropic na ordem primário/secundário e para cross-provider fallback.

### OpenAI utilizável

Verdadeiro quando `OPENAI_API_KEY` não está vazio. Único mecanismo: `api`.

## Modos detalhados

### `anthropic` (default)

1. Tenta API se `ANTHROPIC_API_KEY` presente.
2. Senão ou em falha, tenta Agent SDK.
3. Senão ou em falha, tenta CLI.
4. OpenAI **nunca** é tentado.

### `openai` (estrito)

1. Tenta OpenAI API se `OPENAI_API_KEY` presente e `OPENAI_MODEL` definido (quando a API estiver implementada).
2. Falha → `None`.
3. Anthropic **nunca** é tentado (previsibilidade de conta, custo e comportamento).

### `auto`

1. Resolve `LLM_AUTO_PRIMARY` (default `anthropic`).
2. Monta ordem `[primário, secundário]`.
3. Para cada provider na ordem, se **utilizável** (nível 2 para Anthropic; key para OpenAI), executa a **cadeia completa** desse provider.
4. Primeira resposta não vazia → retorna.
5. Nenhum sucesso → `None`.

Cross-provider fallback: **somente** em `auto`.

| `LLM_AUTO_PRIMARY` | Sequência (ambos utilizáveis) |
|--------------------|-------------------------------|
| `anthropic` | Anthropic API→SDK→CLI, depois OpenAI API |
| `openai` | OpenAI API, depois Anthropic API→SDK→CLI |

## Cross-provider: OpenAI falha → Anthropic?

| `LLM_PROVIDER` | Fallback para Anthropic? |
|----------------|--------------------------|
| `anthropic` | N/A |
| `openai` | **Não** |
| `auto` | **Sim**, se provider Anthropic utilizável (nível 2) |

## Logs

- Início (modo `auto`): `LLM_PROVIDER=auto [auto_primary=<valor>]`
- Tentativa: `provider=<anthropic|openai> mechanism=<api|agent_sdk|cli>`
- Sucesso: `+ <provider>/<mechanism> OK (N chars)`
- Fallback: `! <provider>/<mechanism> falhou (<motivo>), tentando <próximo>`

## Matriz de cenários

| `LLM_PROVIDER` | Ambiente | Provider(s) | Mecanismos |
|----------------|----------|---------------|------------|
| (ausente) | qualquer | Anthropic | API→SDK→CLI |
| `anthropic` | API key | Anthropic | API→… |
| `anthropic` | sem API, CLI ok | Anthropic | SDK→CLI |
| `openai` | OpenAI key + model | OpenAI | API |
| `openai` | sem key | — | `None` |
| `openai` | falha API + key Anthropic | OpenAI apenas | `None` |
| `auto` | ambos + `LLM_AUTO_PRIMARY=anthropic` | Anthropic → OpenAI | cadeias completas |
| `auto` | ambos + `LLM_AUTO_PRIMARY=openai` | OpenAI → Anthropic | cadeias completas |
| `auto` | só OpenAI utilizável | OpenAI | API |
| `auto` | só Anthropic (ex.: CLI) | Anthropic | SDK→CLI |
| `auto` | nenhum utilizável | — | `None` |

## Implementação no código

| Arquivo | Responsabilidade |
|---------|------------------|
| `config.py` | `resolver_llm_provider()`, `resolver_llm_auto_primary()` |
| `llm.py` | **Único ponto de seleção:** `chamar_llm` lê `LLM_PROVIDER` e delega a `_cadeia_anthropic` ou `_cadeia_openai` (modo `auto` com ordem `LLM_AUTO_PRIMARY`) |
| `pipeline.py` | Chama apenas `chamar_llm(...)`; não escolhe provider |

Logs de auditoria em `chamar_llm`:

- `> LLM_PROVIDER=anthropic` ou `> LLM_PROVIDER=openai`
- `> LLM_PROVIDER=auto [auto_primary=<valor>]`

Testes de roteamento: `tests/test_chamar_llm_routing.py`.

## Exemplos `.env`

```env
# Default retrocompativel (equivale a anthropic)
# LLM_PROVIDER=anthropic

# Modo estrito OpenAI (default do projeto: gpt-4o; override opcional)
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o

# Auto com OpenAI primeiro quando ambos existem
# LLM_PROVIDER=auto
# LLM_AUTO_PRIMARY=openai
```
