"""Cliente LLM multi-provider para o pipeline NBR 12721."""
import os
import asyncio
import time
from collections.abc import Awaitable, Callable

from ..settings.config import (
    TIMEOUT_CLAUDE_SDK,
    TIMEOUT_CLAUDE_CLI,
    MODELO_ANTHROPIC_PADRAO,
    MAX_TOKENS_API,
    API_MAX_TENTATIVAS,
    API_BACKOFF_BASE_SEG,
    API_BACKOFF_MAX_SEG,
    resolver_llm_provider,
    resolver_llm_auto_primary,
    resolver_openai_model,
)
from ..extraction.prompts import PROMPT_SISTEMA

import logging

logger = logging.getLogger(__name__)

__all__ = ["chamar_llm"]

_PROVIDER_ANTHROPIC = "anthropic"
_PROVIDER_OPENAI = "openai"


# --- Contrato interno de resposta (ver docs/llm-response-contract.md) ---


def _normalizar_texto_resposta(bruto) -> str | None:
    """Texto consumivel pelo pipeline: strip, CRLF->LF; vazio => None."""
    if bruto is None:
        return None
    if not isinstance(bruto, str):
        logger.warning(f"  ! resposta LLM: tipo inesperado {type(bruto).__name__}, tratando como falha")
        return None
    texto = bruto.strip().replace("\r\n", "\n")
    return texto if texto else None


def _classificar_erro(exc: Exception) -> tuple[bool, str]:
    """Classificacao pragmatica para log; retorno publico continua None."""
    msg = str(exc).lower()
    nome = type(exc).__name__
    if isinstance(exc, ImportError):
        return False, f"{nome}: dependencia ausente"
    if any(s in msg for s in ("rate", "429", "overload", "timeout")):
        return True, f"{nome}: limite ou sobrecarga"
    if any(s in msg for s in ("401", "403", "invalid_api_key", "authentication", "permission")):
        return False, f"{nome}: autenticacao"
    return False, f"{nome}: {exc}"


def _texto_de_resposta_anthropic_api(resp) -> str | None:
    partes = []
    for bloco in getattr(resp, "content", []) or []:
        texto = getattr(bloco, "text", None)
        if texto:
            partes.append(texto)
    return _normalizar_texto_resposta("".join(partes))


def _texto_de_resposta_anthropic_sdk(texto_acumulado) -> str | None:
    return _normalizar_texto_resposta(texto_acumulado)


def _texto_de_resposta_anthropic_cli(stdout) -> str | None:
    return _normalizar_texto_resposta(stdout)


def _texto_de_resposta_openai_api(resp) -> str | None:
    """Extrai texto de chat.completions.create (choices[0].message.content)."""
    if resp is None:
        return None
    choices = getattr(resp, "choices", None) or []
    if not choices:
        return None
    message = getattr(choices[0], "message", None)
    if message is None:
        return None
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return _normalizar_texto_resposta(content)
    if isinstance(content, list):
        partes = []
        for parte in content:
            if isinstance(parte, dict):
                if parte.get("type") == "text" and parte.get("text"):
                    partes.append(parte["text"])
            else:
                texto = getattr(parte, "text", None)
                if texto:
                    partes.append(texto)
        return _normalizar_texto_resposta("".join(partes))
    return None


async def _tentar_mecanismo(
    provider: str,
    mechanism: str,
    obter_bruto: Callable[[], Awaitable],
    adaptar: Callable[[object], str | None],
) -> str | None:
    """Resultado ou excecao final; retry fica dentro do mecanismo (ex.: API)."""
    try:
        bruto = await obter_bruto()
        return adaptar(bruto)
    except Exception as exc:
        _, mensagem = _classificar_erro(exc)
        logger.warning(f"  ! {provider}/{mechanism} falhou ({mensagem})")
        return None


def _tentar_mecanismo_sync(
    provider: str,
    mechanism: str,
    obter_bruto: Callable[[], object],
    adaptar: Callable[[object], str | None],
) -> str | None:
    try:
        bruto = obter_bruto()
        return adaptar(bruto)
    except Exception as exc:
        _, mensagem = _classificar_erro(exc)
        logger.warning(f"  ! {provider}/{mechanism} falhou ({mensagem})")
        return None


def _ler_lista_paths_env(nome_var):
    valor = os.environ.get(nome_var, "").strip()
    if not valor:
        return []
    return [p.strip() for p in valor.split(os.pathsep) if p.strip()]


def _claude_env():
    """Retorna environment com PATH incluindo diretórios comuns do Claude/npm."""
    env = os.environ.copy()
    extras = [
        os.path.expandvars(r"%APPDATA%\npm"),
        os.path.expandvars(r"%APPDATA%\npm\node_modules\.bin"),
        r"C:\Program Files\nodejs",
    ]
    extras.extend(_ler_lista_paths_env("CLAUDE_EXTRA_PATHS"))
    path = env.get("PATH", "")
    for p in extras:
        if p not in path:
            path = p + os.pathsep + path
    env["PATH"] = path
    return env


def _encontrar_claude():
    """Localiza o executável do Claude no sistema."""
    import shutil

    executavel_env = os.environ.get("CLAUDE_EXECUTABLE", "").strip()
    if executavel_env and os.path.exists(executavel_env):
        return executavel_env

    env = _claude_env()
    path_orig = os.environ.get("PATH", "")
    os.environ["PATH"] = env["PATH"]
    cmd = shutil.which("claude") or shutil.which("claude.cmd")
    os.environ["PATH"] = path_orig
    if cmd:
        return cmd
    for p in [
        os.path.expandvars(r"%APPDATA%\npm\claude.cmd"),
        os.path.expandvars(r"%APPDATA%\npm\claude"),
    ]:
        if os.path.exists(p):
            return p
    for p in _ler_lista_paths_env("CLAUDE_CANDIDATE_PATHS"):
        if os.path.exists(p):
            return p
    return None


def _anthropic_api_disponivel():
    """Nivel 1: credencial da API Anthropic."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _anthropic_agent_sdk_disponivel():
    try:
        import claude_agent_sdk  # noqa: F401
        return True
    except ImportError:
        return False


def _anthropic_provider_utilizavel():
    """Nivel 2: pelo menos um mecanismo Anthropic pode ser tentado."""
    return (
        _anthropic_api_disponivel()
        or _anthropic_agent_sdk_disponivel()
        or _encontrar_claude() is not None
    )


def _openai_provider_utilizavel():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def _provider_utilizavel(provider: str) -> bool:
    if provider == _PROVIDER_ANTHROPIC:
        return _anthropic_provider_utilizavel()
    if provider == _PROVIDER_OPENAI:
        return _openai_provider_utilizavel()
    return False


def _ordenar_providers_auto():
    primario = resolver_llm_auto_primary()
    secundario = _PROVIDER_OPENAI if primario == _PROVIDER_ANTHROPIC else _PROVIDER_ANTHROPIC
    return primario, secundario


async def _coletar_claude_sdk(prompt_completo):
    from claude_agent_sdk import query, ClaudeAgentOptions
    resposta = ""
    async for msg in query(
        prompt=prompt_completo,
        options=ClaudeAgentOptions(system_prompt=PROMPT_SISTEMA, max_turns=1),
    ):
        if hasattr(msg, "content"):
            for block in msg.content:
                if hasattr(block, "text"):
                    resposta += block.text
        elif hasattr(msg, "result"):
            r = msg.result
            resposta += r.text if hasattr(r, "text") else (r if isinstance(r, str) else "")
    return resposta


async def chamar_claude_sdk(prompt_completo):
    env = _claude_env()
    os.environ.update({"PATH": env["PATH"]})
    return await asyncio.wait_for(_coletar_claude_sdk(prompt_completo), timeout=TIMEOUT_CLAUDE_SDK)


def _executar_claude_cli(prompt_completo):
    import subprocess
    import tempfile

    claude_cmd = _encontrar_claude()
    if not claude_cmd:
        logger.error("    CLI erro: executavel 'claude' nao encontrado")
        return None
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(prompt_completo)
        pf = f.name
    try:
        r = subprocess.run(
            [claude_cmd, "-p", f"Leia o arquivo {pf} e execute as instrucoes.",
             "--allowedTools", "Read", "--output-format", "text"],
            capture_output=True, text=True, timeout=TIMEOUT_CLAUDE_CLI,
            env=_claude_env(),
        )
        if r.returncode == 0:
            return r.stdout
        logger.error(f"    CLI exit code: {r.returncode}")
        if r.stderr:
            logger.info(f"    CLI stderr: {r.stderr[:500]}")
        if r.stdout:
            logger.info(f"    CLI stdout: {r.stdout[:200]}")
        return None
    except FileNotFoundError:
        logger.error("    CLI erro: 'claude' nao encontrado no PATH")
        return None
    except Exception as e:
        logger.error(f"    CLI erro: {e}")
        return None
    finally:
        os.unlink(pf)


async def chamar_claude_api(prompt_completo, system_prompt=PROMPT_SISTEMA):
    """Retry de rate limit interno; retorna texto normalizado ou None."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None

    def _chamar():
        from anthropic import Anthropic
        cliente = Anthropic(api_key=api_key)
        ultima_exc = None
        for tentativa in range(API_MAX_TENTATIVAS):
            try:
                resp = cliente.messages.create(
                    model=os.environ.get("ANTHROPIC_MODEL", MODELO_ANTHROPIC_PADRAO),
                    max_tokens=MAX_TOKENS_API,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt_completo}],
                )
                return _texto_de_resposta_anthropic_api(resp)
            except Exception as exc:
                ultima_exc = exc
                recuperavel, msg = _classificar_erro(exc)
                if not recuperavel:
                    logger.warning(f"    API falhou ({msg})")
                    return None
                espera = min(API_BACKOFF_MAX_SEG, API_BACKOFF_BASE_SEG * (tentativa + 1))
                logger.warning(f"    API rate limit/overload, aguardando {espera}s para retry...")
                time.sleep(espera)
        if ultima_exc:
            _, msg = _classificar_erro(ultima_exc)
            logger.error(f"    API falhou apos retries ({msg})")
        return None

    return await asyncio.to_thread(_chamar)


async def _cadeia_anthropic(prompt_completo, system_prompt=PROMPT_SISTEMA):
    """Provider anthropic: api -> agent_sdk -> cli."""
    if _anthropic_api_disponivel():
        texto = await _tentar_mecanismo(
            _PROVIDER_ANTHROPIC,
            "api",
            lambda: chamar_claude_api(prompt_completo, system_prompt=system_prompt),
            lambda bruto: _normalizar_texto_resposta(bruto),
        )
        if texto:
            logger.info(f"  + {_PROVIDER_ANTHROPIC}/api OK ({len(texto)} chars)")
            return texto
        logger.warning(f"  ! {_PROVIDER_ANTHROPIC}/api sem resposta, tentando agent_sdk...")
    else:
        logger.warning(f"  ! {_PROVIDER_ANTHROPIC}/api: ANTHROPIC_API_KEY ausente, tentando agent_sdk...")

    if _anthropic_agent_sdk_disponivel():
        texto = await _tentar_mecanismo(
            _PROVIDER_ANTHROPIC,
            "agent_sdk",
            lambda: chamar_claude_sdk(prompt_completo),
            _texto_de_resposta_anthropic_sdk,
        )
        if texto:
            logger.info(f"  + {_PROVIDER_ANTHROPIC}/agent_sdk OK ({len(texto)} chars)")
            return texto
        logger.warning(f"  ! {_PROVIDER_ANTHROPIC}/agent_sdk sem resposta, tentando cli...")
    else:
        logger.warning(f"  ! {_PROVIDER_ANTHROPIC}/agent_sdk nao disponivel, tentando cli...")

    texto = _tentar_mecanismo_sync(
        _PROVIDER_ANTHROPIC,
        "cli",
        lambda: _executar_claude_cli(prompt_completo),
        _texto_de_resposta_anthropic_cli,
    )
    if texto:
        logger.info(f"  + {_PROVIDER_ANTHROPIC}/cli OK ({len(texto)} chars)")
    return texto


async def chamar_openai_api(prompt_completo, system_prompt=PROMPT_SISTEMA):
    """OpenAI Chat Completions; retry de rate limit interno; retorna texto normalizado ou None."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    def _chamar():
        from openai import OpenAI
        cliente = OpenAI(api_key=api_key)
        ultima_exc = None
        for tentativa in range(API_MAX_TENTATIVAS):
            try:
                resp = cliente.chat.completions.create(
                    model=resolver_openai_model(),
                    max_tokens=MAX_TOKENS_API,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt_completo},
                    ],
                )
                return _texto_de_resposta_openai_api(resp)
            except Exception as exc:
                ultima_exc = exc
                recuperavel, msg = _classificar_erro(exc)
                if not recuperavel:
                    logger.warning(f"    OpenAI API falhou ({msg})")
                    return None
                espera = min(API_BACKOFF_MAX_SEG, API_BACKOFF_BASE_SEG * (tentativa + 1))
                logger.warning(f"    OpenAI API rate limit/overload, aguardando {espera}s para retry...")
                time.sleep(espera)
        if ultima_exc:
            _, msg = _classificar_erro(ultima_exc)
            logger.error(f"    OpenAI API falhou apos retries ({msg})")
        return None

    return await asyncio.to_thread(_chamar)


async def _cadeia_openai(prompt_completo, system_prompt=PROMPT_SISTEMA):
    """Provider openai: api apenas."""
    if not _openai_provider_utilizavel():
        logger.warning(f"  ! {_PROVIDER_OPENAI}/api: OPENAI_API_KEY ausente")
        return None

    texto = await _tentar_mecanismo(
        _PROVIDER_OPENAI,
        "api",
        lambda: chamar_openai_api(prompt_completo, system_prompt=system_prompt),
        lambda bruto: _normalizar_texto_resposta(bruto),
    )
    if texto:
        logger.info(f"  + {_PROVIDER_OPENAI}/api OK ({len(texto)} chars)")
    else:
        logger.warning(f"  ! {_PROVIDER_OPENAI}/api sem resposta")
    return texto


async def _executar_provider(provider, prompt_completo, system_prompt):
    if provider == _PROVIDER_ANTHROPIC:
        return await _cadeia_anthropic(prompt_completo, system_prompt=system_prompt)
    if provider == _PROVIDER_OPENAI:
        return await _cadeia_openai(prompt_completo, system_prompt=system_prompt)
    return None


async def chamar_llm(prompt_completo, system_prompt=PROMPT_SISTEMA):
    modo = resolver_llm_provider()

    if modo == _PROVIDER_ANTHROPIC:
        logger.info(f"  > LLM_PROVIDER={modo}")
        return _normalizar_texto_resposta(
            await _cadeia_anthropic(prompt_completo, system_prompt=system_prompt)
        )

    if modo == _PROVIDER_OPENAI:
        logger.info(f"  > LLM_PROVIDER={modo}")
        return _normalizar_texto_resposta(
            await _cadeia_openai(prompt_completo, system_prompt=system_prompt)
        )

    primario, secundario = _ordenar_providers_auto()
    logger.info(f"  > LLM_PROVIDER=auto [auto_primary={primario}]")

    tentou_primario = False
    for provider in (primario, secundario):
        if not _provider_utilizavel(provider):
            logger.warning(f"  ! provider {provider} nao utilizavel, pulando")
            continue
        if tentou_primario:
            logger.warning(f"  ! provider {primario} sem resposta, tentando {provider}")
        resposta = await _executar_provider(provider, prompt_completo, system_prompt)
        texto = _normalizar_texto_resposta(resposta)
        if texto:
            return texto
        tentou_primario = True

    logger.warning("  ! LLM: nenhum provider retornou resposta (modo auto)")
    return None
