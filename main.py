from __future__ import annotations

import asyncio
import io
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

import colorama
from dotenv import load_dotenv
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.application import in_terminal, run_in_terminal
from prompt_toolkit.application.current import get_app_or_none
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style as PTStyle
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from backup_manager import backup_manager
from bridge import AxonBridge
from skills_manager import create_skill_file, ensure_skills_workspace
from skills.tasks import set_plan_render_callback
from task_manager import task_manager
from llm_client import (
    LLMManager,
    TOTAL_COST,
    TOTAL_TOKENS,
    reset_session_counters,
)
from skills.tools import (
    ApprovalDecision,
    clear_session_approvals,
    set_tool_result_callback,
    tool_display_label,
)
from ui.axon_completer import build_axon_completer
from ui.branding import INSTRUCTIONS, VERSION, build_gradient_logo
from ui.completer import AXON_COMMANDS
from ui.file_context import build_file_context
from ui.git_commit import collect_git_changes, run_git_commit
from ui.git_review import build_review_prompt
from ui.theme import DEFAULT_THEME

axon_completer = build_axon_completer()

colorama.just_fix_windows_console()

if os.name == "nt":
    os.system("")  # Enable VT100 ANSI processing on Windows PowerShell/CMD

console = Console(force_terminal=True, color_system="truecolor")
_string_io = io.StringIO()
string_console = Console(
    force_terminal=True,
    color_system="truecolor",
    file=_string_io,
)
MAX_TOOL_OUTPUT = 4000


def parse_image_command(text: str) -> tuple[str, str]:
    """Parse `/image <path> [prompt]` supporting quoted paths."""
    rest = text[6:].strip() if text.lower().startswith("/image") else ""
    if not rest:
        return "", "Analyze this image."

    if rest[0] in "\"'":
        quote = rest[0]
        end = rest.find(quote, 1)
        if end == -1:
            return rest.strip(quote), "Analyze this image."
        path = rest[1:end]
        prompt = rest[end + 1 :].strip() or "Analyze this image."
        return path, prompt

    parts = rest.split(maxsplit=1)
    path = parts[0]
    prompt = parts[1].strip() if len(parts) > 1 else "Analyze this image."
    return path, prompt


def format_display_mentions(display_text: str) -> str:
    """Colorize attached file/dir tags for terminal output."""
    text = re.sub(
        r"\[file:([^\]]+)\]",
        r"[bold cyan]📎 \1[/]",
        display_text,
    )
    text = re.sub(
        r"\[dir:([^\]]+)/\]",
        r"[bold cyan]📁 \1/[/]",
        text,
    )
    return re.sub(
        r"\[missing:@([^\]]+)\]",
        r"[red]✗ @\1 (not found)[/]",
        text,
    )


def clear_terminal() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _prompt_is_active() -> bool:
    app = get_app_or_none()
    return app is not None and app._is_running


def _rich_to_ansi(renderable: Any) -> str:
    """Render a Rich object to an ANSI string via an in-memory buffer."""
    _string_io.seek(0)
    _string_io.truncate(0)
    string_console.print(renderable)
    return _string_io.getvalue()


def safe_print(renderable: Any) -> None:
    """Emit Rich output through prompt_toolkit's native ANSI parser."""
    output = _rich_to_ansi(renderable)
    if output:
        print_formatted_text(ANSI(output))


async def safe_async_print(renderable: Any) -> None:
    """Async-safe emit: suspend prompt, print ANSI via prompt_toolkit, resume."""

    def _emit() -> None:
        safe_print(renderable)

    app = get_app_or_none()
    if app is not None and app._is_running and not app._running_in_terminal:
        await run_in_terminal(_emit)
    else:
        _emit()


def _permission_menu_text(command_detail: str) -> str:
    return (
        f"\n[bold yellow][?] AXON wants to execute a command:[/]\n"
        f"[white]{command_detail}[/]\n"
        f"[bold green]1. Allow once[/]\n"
        f"[bold yellow]2. Allow for this session[/]\n"
        f"[bold red]3. Reject[/]"
    )


def ask_permission(command_detail: str) -> str:
    """Print permission menu via Rich (safe for shell metacharacters), then input."""
    safe_print(_permission_menu_text(command_detail))
    sys.stdout.flush()
    return input("Select (1/2/3): ").strip()


def print_banner(model: str) -> None:
    short_model = model.rsplit("/", 1)[-1]
    console.print()
    console.print(Align.center(build_gradient_logo(DEFAULT_THEME)))
    console.print(
        Align.center(
            f"[dim]v{VERSION} · model: [cyan]{short_model}[/cyan] · {INSTRUCTIONS}[/dim]"
        )
    )
    console.print(Rule(style="dim"))
    console.print()


async def start_axon() -> None:
    load_dotenv()

    workspace = Path.cwd()
    ensure_skills_workspace(workspace)
    backup_manager.set_workspace(workspace)

    llm_manager = LLMManager(workspace=workspace)
    bridge = AxonBridge()
    llm_lock = asyncio.Lock()
    shutdown = asyncio.Event()
    # When True, Rich output must go through safe_print (inside in_terminal).
    background_render = {"active": False}

    session_state = {
        "status": DEFAULT_THEME.status_ready,
        "status_style": DEFAULT_THEME.success,
    }

    tool_history: list[tuple[str, str, str]] = []

    def get_toolbar():
        short_model = llm_manager.model.rsplit("/", 1)[-1]
        markup = DEFAULT_THEME.toolbar_markup.format(
            model=short_model,
            cost=TOTAL_COST,
            status=session_state["status"],
            status_style=session_state["status_style"],
        )
        # Wrap in a simple styled string for prompt_toolkit
        return ANSI(_rich_to_ansi(markup))

    kb = KeyBindings()

    @kb.add("s-tab")
    def _(event):
        """Show recent tool history when Shift+Tab is pressed."""
        if not tool_history:
            return

        def _show_history():
            console.print(Rule("Tool Execution History", style="dim"))
            for name, detail, output in tool_history[-5:]:
                label = tool_display_label(name)
                console.print(f"[bold cyan]✦ {label}[/] [dim]{detail}[/]")
                if output:
                    body = output.strip()
                    if len(body) > 500:
                        body = f"{body[:500]}\n[dim]... (truncated)[/]"
                    console.print(Panel(body, border_style="dim", padding=(0, 1)))
            console.print(Rule(style="dim"))

        asyncio.create_task(run_in_terminal(_show_history))

    session = PromptSession(
        completer=axon_completer,
        complete_while_typing=True,
        history=FileHistory(str(Path.home() / ".axon_history")),
        style=PTStyle.from_dict({
            "prompt": f"{DEFAULT_THEME.accent} bold",
            "bottom-toolbar": f"bg:{DEFAULT_THEME.toolbar_bg} {DEFAULT_THEME.toolbar_text}",
        }),
        bottom_toolbar=get_toolbar,
        key_bindings=kb,
        refresh_interval=0.5,
    )

    async def emit(renderable: Any) -> None:
        if background_render["active"]:
            safe_print(renderable)
        elif _prompt_is_active():
            await safe_async_print(renderable)
        else:
            console.print(renderable)

    async def request_approval(tool_name: str, detail: str) -> ApprovalDecision:
        label = tool_display_label(tool_name)
        display_detail = detail.strip() or "(no details)"
        command_detail = f"{label}: {display_detail}"

        def _ask() -> ApprovalDecision:
            choice = ask_permission(command_detail)
            while choice not in {"1", "2", "3"}:
                safe_print("[red]Invalid choice. Enter 1, 2, or 3.[/]\n")
                sys.stdout.flush()
                choice = input("Select (1/2/3): ").strip()

            decision_map: dict[str, ApprovalDecision] = {
                "1": "once",
                "2": "session",
                "3": "deny",
            }
            decision = decision_map[choice]
            if decision == "deny":
                safe_print("[red][X] Execution denied by user.[/]\n")
                sys.stdout.flush()
            return decision

        app = get_app_or_none()
        if background_render["active"] or (
            app is not None and app._is_running and app._running_in_terminal
        ):
            return _ask()
        if _prompt_is_active():
            return await run_in_terminal(_ask)
        return _ask()

    async def on_tool_result(tool_name: str, detail: str, output: str) -> None:
        label = tool_display_label(tool_name)
        display_detail = detail.strip() or "(no details)"
        
        # Save to history for Shift+Tab navigation
        tool_history.append((tool_name, display_detail, output))
        if len(tool_history) > 20:
            tool_history.pop(0)

        if tool_name == "execute_shell":
            title = f"Shell: {display_detail}"
        elif tool_name == "write_file":
            title = f"Write: {display_detail}"
        else:
            title = f"{label}: {display_detail}"

        # More compact, elegant tool results
        await emit(f"[dim]  [green]✓[/] {title}[/dim]")
        if output and tool_name in {"execute_shell", "read_file", "web_search"}:
            body = output.strip()
            if len(body) > MAX_TOOL_OUTPUT:
                body = f"{body[:MAX_TOOL_OUTPUT]}\n… (truncated)"
            await emit(Panel(body, border_style="dim", padding=(0, 1)))

    llm_manager.set_approval_callback(request_approval)
    set_tool_result_callback(on_tool_result)

    async def render_plan_board() -> None:
        await emit(task_manager.build_plan_panel())

    set_plan_render_callback(render_plan_board)

    async def sync_stats() -> None:
        await bridge.broadcast_stats(TOTAL_TOKENS, TOTAL_COST)

    async def apply_model(
        model: str,
        *,
        announce_cli: bool = True,
        background: bool = False,
    ) -> None:
        llm_manager.set_model(model)
        bridge._current_model = llm_manager.model
        if announce_cli:
            message = f"\n[dim]AXON: Model set to [cyan]{model}[/cyan][/dim]"
            if background:
                await safe_async_print(message)
            else:
                console.print(message)
        await bridge.broadcast_model(model)

    async def run_llm(
        stripped: str,
        *,
        background: bool = False,
        file_context: str = "",
    ):

        async def on_tool(tool_name: str, detail: str) -> None:
            await emit(f"[dim]  [cyan]process[/] {tool_name}...[/dim]")

        llm_manager.set_tool_callback(on_tool)

        status_text = "[bold magenta]AXON is thinking...[/]"
        session_state["status"] = DEFAULT_THEME.status_thinking
        session_state["status_style"] = DEFAULT_THEME.accent
        
        try:
            if background:
                await emit(status_text)
                llm_manager.reload_credentials()
                result = await llm_manager.send_message_async(
                    stripped,
                    file_context=file_context,
                )
            else:
                with console.status(status_text, spinner="dots"):
                    llm_manager.reload_credentials()
                    result = await llm_manager.send_message_async(
                        stripped,
                        file_context=file_context,
                    )
        finally:
            session_state["status"] = DEFAULT_THEME.status_ready
            session_state["status_style"] = DEFAULT_THEME.success

        await emit(f"\n{DEFAULT_THEME.assistant_label}")
        if result.ok and result.content:
            await emit(Markdown(result.content, code_theme="monokai"))
        else:
            await emit(f"[red]{result.display_text}[/]")
        
        await emit(
            f"\n[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n"
        )

        if result.usage:
            await sync_stats()
        return result

    async def run_plan_mode(description: str, *, background: bool = False) -> None:
        await emit(f"\n[bold cyan]❯ You:[/]\n/plan {description}")
        await emit("[bold magenta]📋 Entering Plan Mode — building task board...[/]")

        async with llm_lock:
            try:
                result = await llm_manager.send_plan_async(description)
                await emit("\n[bold green]✦ AXON:[/]")
                if result.ok and result.content:
                    await emit(Markdown(result.content))
                else:
                    await emit(f"[red]{result.display_text}[/]")
                if task_manager.has_plan():
                    await emit(
                        "[dim]Type [cyan]execute[/] to start working through the plan.[/dim]\n"
                    )
                await emit(
                    f"[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n"
                )
                if result.usage:
                    await sync_stats()
            except Exception as exc:
                await emit(f"\n[bold red]✦ AXON:[/] [ERROR]: {exc}\n")

    async def run_execute_mode(*, background: bool = False) -> None:
        if not task_manager.has_plan():
            await emit("[yellow]No active plan. Use /plan <description> first.[/]\n")
            return

        await emit("\n[bold cyan]❯ You:[/]\nexecute")
        await emit("[bold magenta]▶ Executing plan...[/]")
        if not background:
            await render_plan_board()

        async with llm_lock:
            try:
                result = await llm_manager.send_execute_async()
                await emit("\n[bold green]✦ AXON:[/]")
                if result.ok and result.content:
                    await emit(Markdown(result.content))
                else:
                    await emit(f"[red]{result.display_text}[/]")
                await emit(
                    f"[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n"
                )
                if result.usage:
                    await sync_stats()
                if task_manager.all_done():
                    await emit("[green][✓] All plan tasks completed.[/]\n")
            except Exception as exc:
                await emit(f"\n[bold red]✦ AXON:[/] [ERROR]: {exc}\n")

    async def run_create_skill() -> None:
        await emit("[bold magenta]🛠 Creating a new AXON skill[/]\n")

        def _prompt_fields() -> tuple[str, str, str]:
            name = input("Skill Name (e.g., check-logs): ").strip()
            description = input("Description: ").strip()
            shell_cmd = input(
                "Auto-execute shell command (optional, press Enter to skip): "
            ).strip()
            return name, description, shell_cmd

        app = get_app_or_none()
        if _prompt_is_active():
            name, description, shell_cmd = await run_in_terminal(_prompt_fields)
        else:
            name, description, shell_cmd = _prompt_fields()

        if not name:
            await emit("[red]Skill name is required.[/]\n")
            return
        if not description:
            await emit("[red]Description is required.[/]\n")
            return

        try:
            path = create_skill_file(
                name,
                description,
                shell_cmd,
                workspace=workspace,
            )
            llm_manager.reload_skills()
            await emit(
                f"[green][✓] Skill created successfully![/] "
                f"AXON can now use [cyan]{path.parent.name}[/cyan].\n"
            )
        except OSError as exc:
            await emit(f"[red]Failed to create skill — {exc}[/]\n")

    async def run_review(*, background: bool = False) -> None:
        prompt, error = build_review_prompt(workspace)
        if error:
            await emit(f"[red]{error}[/]\n")
            return

        await emit("\n[bold cyan]❯ You:[/]\n/review")
        await emit("[bold magenta]🔍 Reviewing git changes...[/]")

        async with llm_lock:
            await run_llm(
                prompt,
                background=background,
            )

    async def run_undo() -> None:
        backup_manager.set_workspace(workspace)
        ok, detail = backup_manager.undo_last()
        if ok:
            await emit(
                f"[green][✓] File {detail} restored to previous state.[/]\n"
            )
        else:
            await emit(f"[yellow]{detail}[/]\n")

    async def run_commit(*, background: bool = False) -> None:
        status, diff, error = collect_git_changes(workspace)
        if error:
            await emit(f"[red]{error}[/]\n")
            return

        await emit("\n[bold cyan]❯ You:[/]\n/commit")
        await emit("[bold magenta]📝 Generating commit message...[/]")

        async with llm_lock:
            result = await llm_manager.generate_commit_message_async(status, diff)

        if not result.ok:
            await emit(f"[red]{result.display_text}[/]\n")
            return

        message = result.content.strip()

        def _confirm() -> str:
            safe_print(
                f'\n[bold yellow][?] Commit with message:[/] "{message}"? (y/n)'
            )
            sys.stdout.flush()
            return input().strip().lower()

        app = get_app_or_none()
        if background_render["active"] or (
            app is not None and app._is_running and app._running_in_terminal
        ):
            answer = _confirm()
        elif _prompt_is_active():
            answer = await run_in_terminal(_confirm)
        else:
            answer = _confirm()

        if answer not in {"y", "yes"}:
            await emit("[dim]Commit cancelled.[/]\n")
            return

        ok, output = run_git_commit(message, workspace)
        if ok:
            await emit(f"[green][✓] {output}[/]\n")
        else:
            await emit(f"[red]{output}[/]\n")

        if result.usage:
            await sync_stats()

    async def run_docs() -> None:
        script = workspace / "scripts" / "docs_gen.py"
        if not script.is_file():
            await emit("[red]AXON: scripts/docs_gen.py not found.[/]\n")
            return

        await emit("\n[bold cyan]❯ You:[/]\n/docs")
        await emit("[bold magenta]📚 Generating Live Docs...[/]")

        def _generate() -> tuple[int, str]:
            proc = subprocess.run(
                [sys.executable, str(script), "--workspace", str(workspace)],
                cwd=str(workspace),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode, output.strip()

        try:
            code, output = await asyncio.to_thread(_generate)
        except subprocess.TimeoutExpired:
            await emit("[red]AXON: Docs generation timed out.[/]\n")
            return
        except OSError as exc:
            await emit(f"[red]AXON: Could not run docs generator — {exc}[/]\n")
            return

        if code != 0:
            detail = output or "docs_gen.py failed"
            await emit(f"[red]{detail}[/]\n")
            return

        if output:
            for line in output.splitlines():
                if line.strip():
                    await emit(f"[dim]{line}[/]\n")

        await emit("[green][✓] Docs available at http://localhost:8000[/]\n")

    async def execute_slash_command(stripped: str, *, background: bool = False) -> bool:
        """Handle slash commands locally — returns True if handled (no LLM call)."""
        if not stripped.startswith("/"):
            return False

        parts = stripped.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "/exit":
            await emit("[dim]AXON: Goodbye.[/dim]")
            shutdown.set()
            return True

        if cmd == "/help":
            lines = [
                f"  [cyan]{name:<10}[/] {desc}"
                for name, desc in AXON_COMMANDS.items()
            ]
            await emit("[bold]AXON Commands[/bold]\n" + "\n".join(lines) + "\n")
            return True

        if cmd == "/clear":
            reset_session_counters()
            clear_session_approvals()
            task_manager.clear()
            llm_manager.messages = [llm_manager.messages[0]]
            llm_manager.reload_skills()
            await sync_stats()
            await emit("[green][✓] Context cleared.[/]\n")
            return True

        if cmd in {"/cost", "/usage"}:
            await emit(
                f"[dim]Cost: [cyan]${TOTAL_COST:.4f}[/cyan] · "
                f"Tokens: [cyan]{TOTAL_TOKENS}[/cyan][/dim]\n"
            )
            return True

        if cmd == "/compact":
            await emit(
                "[dim][i] Compacting context... (Feature coming soon)[/][/dim]\n"
            )
            return True

        if cmd == "/model":
            if args.strip():
                await apply_model(args.strip(), background=background)
                await emit("[green][✓] Model changed.[/]\n")
            else:
                await emit(
                    f"[dim]Current model: [cyan]{llm_manager.model}[/cyan][/dim]\n"
                )
            return True

        if cmd == "/image":
            image_path, prompt = parse_image_command(stripped)
            if not image_path:
                await emit("[yellow]Usage: /image <path> [prompt][/]\n")
                return True
            error = llm_manager.load_image_into_context(image_path, prompt)
            if error:
                await emit(f"[red]{error}[/]\n")
            else:
                await emit("[green][✓] Image loaded into context.[/]\n")
            return True

        if cmd == "/create-skill":
            await run_create_skill()
            return True

        if cmd == "/review":
            await run_review(background=background)
            return True

        if cmd == "/undo":
            await run_undo()
            return True

        if cmd == "/commit":
            await run_commit(background=background)
            return True

        if cmd == "/docs":
            await run_docs()
            return True

        await emit(f"[yellow]AXON: Unknown command {cmd}. Type /help.[/]\n")
        return True

    async def process_user_message(text: str, source: str = "terminal") -> None:
        background = source == "web"

        async def _handle() -> None:
            stripped = text.strip()
            if not stripped:
                return

            if stripped.startswith("/"):
                if stripped.lower().startswith("/plan"):
                    description = stripped[5:].strip()
                    if description:
                        await run_plan_mode(description, background=background)
                    else:
                        await emit("[yellow]Usage: /plan <description>[/]\n")
                    return
                await execute_slash_command(stripped, background=background)
                return

            lowered = stripped.lower()
            if lowered in {"execute", "go", "run"} and task_manager.has_plan():
                await run_execute_mode(background=background)
                return

            display_text, file_context = build_file_context(stripped, workspace)

            if background:
                await emit(f"\n[bold blue]🌐 Web User:[/]\n{stripped}")
            else:
                await emit(f"\n{DEFAULT_THEME.user_label}")
                await emit(format_display_mentions(display_text))
                if file_context:
                    await emit(
                        "[dim]  [cyan]context[/] attached file data sent to AXON[/dim]"
                    )

            if source == "terminal":
                await bridge.broadcast_chat(
                    role="user",
                    text=stripped,
                    source="terminal",
                    message_id=f"terminal-user-{uuid.uuid4().hex[:8]}",
                )

            async with llm_lock:
                try:
                    result = await run_llm(
                        stripped,
                        background=background,
                        file_context=file_context,
                    )
                    await bridge.broadcast_chat(
                        role="assistant",
                        text=result.display_text,
                        source=source,
                        message_id=f"{source}-axon-{uuid.uuid4().hex[:8]}",
                    )
                except Exception as exc:
                    error_text = f"[ERROR]: {exc}"
                    await emit(f"\n[bold red]✦ AXON:[/] {error_text}\n")
                    await bridge.broadcast_chat(
                        role="assistant",
                        text=error_text,
                        source=source,
                    )

        if background:
            async with in_terminal():
                background_render["active"] = True
                try:
                    await _handle()
                finally:
                    background_render["active"] = False
        else:
            await _handle()

    bridge.configure(
        process_chat=process_user_message,
        set_model=lambda model: apply_model(
            model, announce_cli=True, background=True
        ),
        refresh_ui=lambda: None,
        current_model=llm_manager.model,
    )

    ws_server = await bridge.start()

    clear_terminal()
    print_banner(llm_manager.model)

    async def chat_loop() -> None:
        while not shutdown.is_set():
            try:
                with patch_stdout():
                    user_input = await session.prompt_async("AXON ❯ ")
            except (EOFError, KeyboardInterrupt):
                break

            stripped = user_input.strip()
            if not stripped:
                continue

            if stripped.lower().startswith("/plan"):
                description = stripped[5:].strip()
                if not description:
                    await emit("[yellow]Usage: /plan <description>[/]\n")
                    continue
                await run_plan_mode(description)
                if shutdown.is_set():
                    break
                continue

            if stripped.lower() in {"execute", "go", "run"} and task_manager.has_plan():
                await run_execute_mode()
                if shutdown.is_set():
                    break
                continue

            if stripped.lower() == "/commit":
                await run_commit()
                if shutdown.is_set():
                    break
                continue

            if stripped.startswith("/"):
                await execute_slash_command(stripped)
                if shutdown.is_set():
                    break
                continue

            await process_user_message(user_input, "terminal")
            if shutdown.is_set():
                break

    try:
        await chat_loop()
    finally:
        if ws_server is not None:
            ws_server.close()
            await ws_server.wait_closed()


def main() -> None:
    asyncio.run(start_axon())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
