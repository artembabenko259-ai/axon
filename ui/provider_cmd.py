"""REPL/TUI `/provider` — LLM provider, base URL, and API key."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from config_store import (
    CONFIG_PATH,
    get_custom_api_key,
    get_custom_base_url,
    get_model,
    get_ollama_base_url,
    get_openrouter_api_key,
    get_provider,
    save_provider_settings,
)
from provider_config import PROVIDERS, normalize_base_url

Emit = Callable[[Any], Awaitable[None]]

_VALID = set(PROVIDERS)


def _mask_key(key: str) -> str:
    key = key.strip()
    if not key:
        return "(not set)"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}…{key[-4:]}"


def format_provider_status() -> str:
    provider = get_provider()
    lines = [
        f"[bold]LLM provider[/] [dim]{CONFIG_PATH}[/]",
        "",
        f"  provider           {provider}",
        f"  model              {get_model()}",
    ]
    if provider == "openrouter":
        lines.append(f"  api_key            {_mask_key(get_openrouter_api_key())}")
        lines.append("  base_url           https://openrouter.ai/api/v1")
    elif provider == "ollama":
        lines.append(f"  base_url           {get_ollama_base_url()}")
        lines.append("  api_key            (not required)")
    else:
        lines.append(f"  base_url           {get_custom_base_url() or '(not set)'}")
        lines.append(f"  api_key            {_mask_key(get_custom_api_key())}")
    lines.extend(
        [
            "",
            "[dim]/provider set <openrouter|ollama|custom>[/]",
            "[dim]/provider url <base-url>[/]",
            "[dim]/provider key <api-key>[/]",
            "[dim]/provider custom <base-url> <api-key>[/]",
        ]
    )
    return "\n".join(lines)


async def handle_provider_command(stripped: str, *, emit: Emit) -> bool:
    if not stripped.lower().startswith("/provider"):
        return False

    parts = stripped.split(maxsplit=3)
    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub in {"", "show", "status"}:
        await emit(format_provider_status() + "\n")
        return True

    if sub == "set":
        if len(parts) < 3:
            await emit(
                "[yellow]Usage: /provider set <openrouter|ollama|custom>[/]\n"
            )
            return True
        name = parts[2].strip().lower()
        if name not in _VALID:
            await emit(
                f"[red]Unknown provider: {name}[/]\n"
                "[dim]Use openrouter, ollama, or custom.[/]\n"
            )
            return True
        save_provider_settings(provider=name)
        await emit(f"[green][✓] provider = {name}[/]\n")
        return True

    if sub == "url":
        if len(parts) < 3:
            await emit("[yellow]Usage: /provider url <base-url>[/]\n")
            return True
        url = normalize_base_url(parts[2].strip())
        provider = get_provider()
        if provider == "openrouter":
            await emit(
                "[yellow]OpenRouter URL is fixed. Switch with /provider set custom[/]\n"
            )
            return True
        if provider == "ollama":
            save_provider_settings(ollama_base_url=url)
        else:
            save_provider_settings(custom_base_url=url)
        await emit(f"[green][✓] base_url = {url}[/]\n")
        return True

    if sub == "key":
        if len(parts) < 3:
            await emit("[yellow]Usage: /provider key <api-key>[/]\n")
            return True
        key = parts[2].strip()
        provider = get_provider()
        if provider == "ollama":
            await emit("[yellow]Ollama does not need an API key.[/]\n")
            return True
        if provider == "openrouter":
            save_provider_settings(openrouter_api_key=key)
        else:
            save_provider_settings(custom_api_key=key)
        await emit("[green][✓] API key saved[/]\n")
        return True

    if sub == "custom":
        if len(parts) < 4:
            await emit(
                "[yellow]Usage: /provider custom <base-url> <api-key>[/]\n"
                '[dim]Example: /provider custom https://api.groq.com/openai/v1 gsk_...[/]\n'
            )
            return True
        url = normalize_base_url(parts[2].strip())
        key = parts[3].strip()
        save_provider_settings(
            provider="custom",
            custom_base_url=url,
            custom_api_key=key,
        )
        await emit(f"[green][✓] custom provider → {url}[/]\n")
        return True

    await emit(
        "[yellow]Usage: /provider | /provider set <name> | "
        "/provider url <url> | /provider key <key> | "
        "/provider custom <url> <key>[/]\n"
    )
    return True
