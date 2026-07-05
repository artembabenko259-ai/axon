"""REPL `/config` — view and edit runtime_policy.json."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from runtime_policy import (
    POLICY_PATH,
    RuntimePolicy,
    load_runtime_policy,
    save_runtime_policy,
)

Emit = Callable[[Any], Awaitable[None]]

_BOOL_KEYS = frozenset(
    {
        "autonomy_enabled",
        "web_control_enabled",
        "terminal_control_enabled",
        "require_desktop_confirmation",
        "allow_parallel_agents",
        "bridge_auth_enabled",
        "notifications_enabled",
        "sound_on_approval",
        "sound_on_complete",
        "auto_save_session",
    }
)

_FLOAT_KEYS = frozenset({"notification_volume"})


def _parse_value(raw: str) -> Any:
    lowered = raw.strip().lower()
    if lowered in {"true", "1", "yes", "on"}:
        return True
    if lowered in {"false", "0", "no", "off"}:
        return False
    try:
        if "." in lowered:
            return float(lowered)
    except ValueError:
        pass
    return raw


def _format_policy(policy: RuntimePolicy) -> str:
    from autopilot_mode import is_autopilot_active, is_process_elevated

    autopilot_active = is_autopilot_active()
    lines = [
        f"[bold]Runtime policy[/] [dim]{POLICY_PATH}[/]",
        "",
        f"  autonomy_enabled              {policy.autonomy_enabled}",
        f"  autopilot_enabled             {policy.autopilot_enabled}",
        f"  autopilot_active              {autopilot_active}",
        f"  process_elevated              {is_process_elevated()}",
        f"  allow_parallel_agents         {policy.allow_parallel_agents}",
        f"  auto_save_session             {policy.auto_save_session}",
        f"  notifications_enabled         {policy.notifications_enabled}",
        f"  sound_on_approval             {policy.sound_on_approval}",
        f"  sound_on_complete             {policy.sound_on_complete}",
        f"  notification_volume           {policy.notification_volume}",
        f"  web_control_enabled           {policy.web_control_enabled}",
        f"  terminal_control_enabled      {policy.terminal_control_enabled}",
        f"  require_desktop_confirmation  {policy.require_desktop_confirmation}",
        f"  bridge_auth_enabled           {policy.bridge_auth_enabled}",
        f"  telegram_bot_token            {policy.telegram_bot_token or '(empty)'}",
        f"  telegram_chat_id              {policy.telegram_chat_id or '(empty)'}",
        "",
        "[dim]/config set <key> <value>  ·  /autopilot on|off  ·  /config path[/]",
    ]
    return "\n".join(lines)


async def handle_config_command(stripped: str, *, emit: Emit) -> bool:
    if not stripped.lower().startswith("/config"):
        return False

    parts = stripped.split(maxsplit=3)
    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub in {"", "show"}:
        policy = load_runtime_policy()
        await emit(_format_policy(policy) + "\n")
        return True

    if sub == "path":
        await emit(f"{POLICY_PATH}\n")
        return True

    if sub == "set":
        if len(parts) < 4:
            await emit(
                "[yellow]Usage: /config set <key> <value>[/]\n"
                "[dim]Keys: allow_parallel_agents, auto_save_session, autonomy_enabled, "
                "notifications_enabled, sound_on_approval, sound_on_complete[/]\n"
            )
            return True
        key = parts[2].strip()
        if key in {"autopilot_enabled", "autopilot_enabled_at"}:
            await emit(
                "[yellow]Use /autopilot on|off to control Autopilot (requires admin).[/]\n"
            )
            return True
        value_raw = parts[3].strip()
        policy = load_runtime_policy()
        if not hasattr(policy, key):
            await emit(f"[red]Unknown policy key: {key}[/]\n")
            return True
        parsed = _parse_value(value_raw)
        if key in _BOOL_KEYS and not isinstance(parsed, bool):
            await emit(f"[red]Expected boolean for {key}[/]\n")
            return True
        if key in _FLOAT_KEYS:
            try:
                parsed = float(value_raw)
            except ValueError:
                await emit(f"[red]Expected number for {key}[/]\n")
                return True
        setattr(policy, key, parsed)
        save_runtime_policy(policy)
        await emit(f"[green][✓] {key} = {parsed}[/]\n")
        return True

    await emit(
        "[yellow]Usage: /config | /config set <key> <value> | /config path[/]\n"
    )
    return True
