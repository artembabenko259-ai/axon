from __future__ import annotations

from typing import TYPE_CHECKING, Awaitable, Callable

from rich.panel import Panel
from rich.text import Text

from system_prompt_store import (
    clear_global_system_prompt,
    edit_text_in_editor,
    get_global_system_prompt,
    global_prompt_path,
    preview_text,
    save_global_system_prompt,
)
from ui.theme import CLITheme

if TYPE_CHECKING:
    from llm_client import LLMManager

Emit = Callable[[object], Awaitable[None]]


def system_command_usage() -> str:
    return (
        "[bold]System prompt[/]\n"
        "  [cyan]/system[/]                     Show active prompts\n"
        "  [cyan]/system session <text>[/]       Session-only instructions\n"
        "  [cyan]/system global <text>[/]        Persistent instructions (all runs)\n"
        "  [cyan]/system edit[/]                 Edit global prompt in $EDITOR\n"
        "  [cyan]/system edit session[/]         Edit session prompt in $EDITOR\n"
        "  [cyan]/system clear session[/]         Remove session prompt\n"
        "  [cyan]/system clear global[/]          Remove global prompt\n"
        "\n"
        "[dim]Global file:[/] "
        f"[cyan]{global_prompt_path()}[/]\n"
    )


async def handle_system_command(
    stripped: str,
    *,
    llm_manager: "LLMManager",
    emit: Emit,
    theme: CLITheme,
) -> bool:
    if not stripped.lower().startswith("/system"):
        return False

    tail = stripped[len("/system") :].strip()
    if not tail:
        await _show_status(llm_manager, emit, theme)
        return True

    parts = tail.split(maxsplit=1)
    action = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if action in {"help", "?"}:
        await emit(system_command_usage())
        return True

    if action == "show":
        await _show_status(llm_manager, emit, theme)
        return True

    if action == "session":
        if not arg:
            await emit("[yellow]Usage: /system session <instructions>[/]\n")
            return True
        llm_manager.set_session_system_prompt(arg)
        await emit(
            "[green][✓] Session system prompt updated.[/]\n"
            f"[dim]{preview_text(arg)}[/]\n"
        )
        return True

    if action == "global":
        if not arg:
            await emit("[yellow]Usage: /system global <instructions>[/]\n")
            return True
        path = save_global_system_prompt(arg)
        llm_manager.refresh_system_prompt()
        await emit(
            "[green][✓] Global system prompt saved.[/]\n"
            f"[dim]{path}[/]\n"
            f"[dim]{preview_text(arg)}[/]\n"
        )
        return True

    if action == "edit":
        scope = (arg or "global").lower()
        if scope not in {"global", "session"}:
            await emit("[yellow]Usage: /system edit [global|session][/]\n")
            return True

        if scope == "global":
            current = get_global_system_prompt()
            updated = edit_text_in_editor(
                current,
                comment="AXON global system prompt — saved for all future sessions.",
            )
            if updated is None:
                await emit("[dim]Edit cancelled — no changes.[/]\n")
                return True
            path = save_global_system_prompt(updated)
            llm_manager.refresh_system_prompt()
            await emit(
                "[green][✓] Global system prompt saved.[/]\n"
                f"[dim]{path}[/]\n"
            )
            return True

        current = llm_manager.session_system_prompt
        updated = edit_text_in_editor(
            current,
            comment="AXON session system prompt — cleared when you exit AXON.",
        )
        if updated is None:
            await emit("[dim]Edit cancelled — no changes.[/]\n")
            return True
        llm_manager.set_session_system_prompt(updated)
        await emit("[green][✓] Session system prompt updated.[/]\n")
        return True

    if action == "clear":
        target = (arg or "session").lower()
        if target == "session":
            llm_manager.clear_session_system_prompt()
            await emit("[green][✓] Session system prompt cleared.[/]\n")
            return True
        if target == "global":
            clear_global_system_prompt()
            llm_manager.refresh_system_prompt()
            await emit("[green][✓] Global system prompt cleared.[/]\n")
            return True
        await emit("[yellow]Usage: /system clear [session|global][/]\n")
        return True

    await emit(system_command_usage())
    return True


async def _show_status(
    llm_manager: "LLMManager",
    emit: Emit,
    theme: CLITheme,
) -> None:
    global_prompt = get_global_system_prompt()
    session_prompt = llm_manager.session_system_prompt

    body = Text()
    body.append("Global (all sessions)\n", style=theme.accent_soft)
    if global_prompt:
        body.append(preview_text(global_prompt, 400) + "\n", style=theme.text_primary)
        body.append(f"{global_prompt_path()}\n\n", style=theme.text_muted)
    else:
        body.append("(not set)\n\n", style=theme.text_muted)

    body.append("Session (this run)\n", style=theme.accent_soft)
    if session_prompt:
        body.append(preview_text(session_prompt, 400) + "\n", style=theme.text_primary)
    else:
        body.append("(not set)\n", style=theme.text_muted)

    await emit(Panel(body, title="System Prompt", border_style=theme.accent))
