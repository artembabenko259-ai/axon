from __future__ import annotations

import asyncio
import contextlib
import io
import os
import re
import subprocess
import sys
import uuid
from contextlib import asynccontextmanager
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

from agent_manager import create_agent, list_agents
from backup_manager import backup_manager
from approval_bridge import create_approval_waiter
from bridge import AxonBridge
from command_parser import is_command_chain, split_command_chain
from skills_manager import (
    create_skill_file,
    ensure_skills_workspace,
    parse_gen_skill_description,
    save_generated_skill_file,
)
from skills.tasks import set_multitask_runner, set_plan_render_callback
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
    format_tool_activity,
    format_tool_activity_line,
    tool_activity_detail,
)
from ui.axon_completer import build_axon_completer
from ui.agent_intent import detect_intent
from ui.branding import INSTRUCTIONS, VERSION, build_gradient_logo
from ui.explore_stats import get_turn_explore_summary
from ui.config_cmd import handle_config_command
from ui.provider_cmd import handle_provider_command
from ui.autopilot_cmd import handle_autopilot_command
from message_router import try_chitchat_reply
from orchestrator import Orchestrator
from plugins.loader import discover_plugins, list_plugin_commands
from request_context import get_request_source, reset_request_source, set_request_source
from runtime_policy import load_runtime_policy
from mcp_client import load_mcp_servers, save_mcp_servers, McpServer
from session_store import list_sessions, load_session, save_session
from config_store import get_model
from provider_config import is_llm_configured, provider_config_hint
from zenith_server import config_url, has_bundled_zenith, panel_url
from ui.system_prompt_cmd import handle_system_command
from ui.welcome import build_welcome_screen, should_show_welcome
from ui.file_context import build_file_context
from ui.git_commit import collect_git_changes, run_git_commit
from ui.git_review import build_review_prompt
from axon_runtime import bundle_root, install_root
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
    from ui.image_cmd import parse_image_command as _parse

    return _parse(text)


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
    return input(
        "Choose: [1] allow once  [2] allow session  [3] deny — enter 1/2/3: "
    ).strip()


def print_banner(model: str, workspace: Path | None = None) -> None:
    if should_show_welcome():
        console.print()
        console.print(
            build_welcome_screen(
                DEFAULT_THEME,
                model=model,
                workspace=workspace or Path.cwd(),
            )
        )
        console.print()
        return

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


async def start_axon(headless: bool = False) -> None:
    load_dotenv()

    workspace = Path.cwd()
    ensure_skills_workspace(workspace)
    backup_manager.set_workspace(workspace)

    llm_manager = LLMManager(workspace=workspace)
    bridge = AxonBridge()
    agent_lock = asyncio.Lock()
    agent_semaphore = asyncio.Semaphore(3)
    shutdown = asyncio.Event()
    active_generation: dict[str, asyncio.Task[Any] | None] = {"task": None}
    current_session_id: dict[str, str | None] = {"id": None}

    @asynccontextmanager
    async def agent_slot():
        policy = load_runtime_policy()
        if policy.allow_parallel_agents:
            await agent_semaphore.acquire()
            try:
                yield
            finally:
                agent_semaphore.release()
        else:
            async with agent_lock:
                yield

    # When True, Rich output must go through safe_print (inside in_terminal).
    background_render = {"active": False}

    session_state = {
        "status": DEFAULT_THEME.status_ready,
        "status_style": DEFAULT_THEME.success,
    }

    tool_history: list[tuple[str, str, str]] = []
    loaded_plugins = discover_plugins(workspace)

    def plugin_commands() -> dict[str, str]:
        return list_plugin_commands(workspace)

    def merged_help_commands() -> dict[str, str]:
        merged = dict(AXON_COMMANDS)
        merged.update(plugin_commands())
        return merged

    async def try_plugin_command(stripped: str) -> bool:
        if not stripped.startswith("/"):
            return False
        cmd_name = stripped.split(maxsplit=1)[0].lstrip("/").lower()
        args = stripped.split(maxsplit=1)[1] if " " in stripped.strip() else ""
        for plugin in loaded_plugins:
            if cmd_name not in plugin.commands:
                continue
            try:
                result = plugin.run(cmd_name, *args.split())
                text = str(result) if result is not None else "(ok)"
                await emit(f"[green]{text}[/]\n")
            except Exception as exc:
                await emit(f"[red]Plugin {plugin.name} failed — {exc}[/]\n")
            return True
        return False

    async def maybe_auto_save_session() -> None:
        policy = load_runtime_policy()
        if not policy.auto_save_session:
            return
        user_msgs = [
            m for m in llm_manager.messages if m.get("role") == "user"
        ]
        if not user_msgs:
            return
        from datetime import datetime

        title = f"auto-{datetime.now().strftime('%Y-%m-%d-%H%M')}"
        await persist_session(title=title)
        await emit(f"[dim]Session auto-saved as {current_session_id['id']}[/]\n")

    def get_toolbar():
        import shutil
        cols, _ = shutil.get_terminal_size()
        
        border_char = "─"
        border_line = border_char * (cols - 1)
        
        left_text = "? for shortcuts · type /help for commands"
        
        short_model = llm_manager.model.rsplit("/", 1)[-1]
        status = session_state["status"].lower()
        right_text = f"{short_model} · {status}"
        
        # Calculate padding so right_text is right-aligned
        pad_len = cols - len(left_text) - len(right_text) - 1
        if pad_len < 1:
            pad_len = 1
            
        return [
            ("class:bottom-toolbar.border", border_line + "\n"),
            ("class:bottom-toolbar.text", left_text),
            ("class:bottom-toolbar.text", " " * pad_len),
            ("class:bottom-toolbar.text", right_text),
        ]

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
                activity = format_tool_activity_line(label, detail)
                console.print(f"[bold cyan]{activity}[/]")
                if output:
                    body = output.strip()
                    if len(body) > 500:
                        body = f"{body[:500]}\n[dim]... (truncated)[/]"
                    console.print(Panel(body, border_style="dim", padding=(0, 1)))
            console.print(Rule(style="dim"))

        asyncio.create_task(run_in_terminal(_show_history))

    session = None
    if not headless:
        session = PromptSession(
            completer=axon_completer,
            complete_while_typing=True,
            history=FileHistory(str(Path.home() / ".axon_history")),
            style=PTStyle.from_dict({
                "prompt": f"{DEFAULT_THEME.accent} bold",
                "bottom-toolbar": f"fg:{DEFAULT_THEME.text_muted}",
                "bottom-toolbar.border": f"fg:{DEFAULT_THEME.border_subtle}",
                "bottom-toolbar.text": f"fg:{DEFAULT_THEME.text_muted}",
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
        from ui.code_diff import split_approval_message

        label = tool_display_label(tool_name)
        display_detail, preview = split_approval_message(detail)
        command_detail = f"{label}: {display_detail or '(no details)'}"
        policy = load_runtime_policy()
        source = get_request_source()

        if source == "web" and not policy.web_control_enabled:
            return "deny"

        from autopilot_mode import is_autopilot_active

        if is_autopilot_active() or policy.autonomy_enabled:
            return "once"

        from axon_notifications import notify_approval_needed

        notify_approval_needed(tool_name, detail)

        if preview.strip():
            from ui.side_by_side_diff import render_side_by_side_from_diff
            diff_table = render_side_by_side_from_diff(preview, 100)
            await emit(diff_table)

        def _ask() -> ApprovalDecision:
            choice = ask_permission(command_detail)
            while choice not in {"1", "2", "3"}:
                safe_print("[red]Invalid choice. Enter 1, 2, or 3.[/]\n")
                sys.stdout.flush()
                choice = input(
                    "Choose: [1] allow once  [2] allow session  [3] deny — enter 1/2/3: "
                ).strip()

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

        if source == "web" and policy.require_desktop_confirmation:
            await bridge.broadcast_approval_request(tool_name, command_detail)
            await emit(
                "[bold yellow]⚠ Web action needs confirmation in this terminal[/]\n"
                f"[white]{command_detail}[/]\n"
            )

            def _ask_web() -> ApprovalDecision:
                return _ask()

            return await run_in_terminal(_ask_web)

        if source == "web" and not policy.require_desktop_confirmation:
            approval_id, future = create_approval_waiter()
            await bridge.broadcast(
                {
                    "type": "approval_request",
                    "id": approval_id,
                    "tool": tool_name,
                    "detail": command_detail,
                }
            )
            try:
                return await asyncio.wait_for(future, timeout=120)
            except asyncio.TimeoutError:
                return "deny"

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
        activity = format_tool_activity_line(label, display_detail)
        
        # Save to history for Shift+Tab navigation
        tool_history.append((tool_name, display_detail, output))
        if len(tool_history) > 20:
            tool_history.pop(0)

        await bridge.broadcast_tool_event(tool_name, "done", activity)
        if tool_name == "take_screenshot":
            await emit(f"[dim]  [cyan]👁[/] {output.strip()}[/dim]")
            return
        await emit(f"[dim]  [green]✓[/] {activity}[/dim]")
        if output and tool_name in {"execute_shell", "read_file", "web_search"}:
            body = output.strip()
            if len(body) > MAX_TOOL_OUTPUT:
                body = f"{body[:MAX_TOOL_OUTPUT]}\n… (truncated)"
            await emit(Panel(body, border_style="dim", padding=(0, 1)))

    llm_manager.set_approval_callback(request_approval)
    set_tool_result_callback(on_tool_result)

    async def render_plan_board() -> None:
        await emit(task_manager.build_plan_panel())
        await bridge.broadcast_plan_update(
            [
                {"id": t.id, "name": t.name, "status": t.status}
                for t in task_manager.tasks
            ],
            goal=task_manager.goal,
        )

    set_plan_render_callback(render_plan_board)

    async def multitask_for_tool(goal: str) -> str:
        policy = load_runtime_policy()
        orch = Orchestrator(
            llm=llm_manager,
            workspace=workspace,
            allow_parallel=policy.allow_parallel_agents,
        )

        def _subtask_payload(subtasks: list) -> list[dict[str, object]]:
            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "agent": task.agent,
                    "status": task.status,
                }
                for task in subtasks
            ]

        async def on_multitask_event(
            phase: str,
            event_goal: str,
            subtasks: list,
            synthesis: str = "",
        ) -> None:
            await bridge.broadcast_multitask_update(
                phase,
                event_goal,
                _subtask_payload(subtasks),
                synthesis=synthesis,
            )

        result = await orch.run(
            goal,
            on_multitask_event=on_multitask_event,
        )
        if result.error and not result.synthesis:
            return result.error
        return result.synthesis or "(empty)"

    set_multitask_runner(multitask_for_tool)

    async def persist_session(title: str | None = None) -> None:
        meta = save_session(
            session_id=current_session_id["id"],
            messages=llm_manager.messages,
            model=llm_manager.model,
            tokens=TOTAL_TOKENS,
            title=title,
        )
        current_session_id["id"] = meta.id

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
            message = (
                f"\n[dim]AXON: Model set to [cyan]{llm_manager.model}[/cyan][/dim]"
            )
            if background:
                await safe_async_print(message)
            else:
                console.print(message)
        await bridge.broadcast_model(llm_manager.model)

    async def run_llm(
        stripped: str,
        *,
        background: bool = False,
        file_context: str = "",
        source: str = "terminal",
    ):
        stream_id = f"{source}-stream-{uuid.uuid4().hex[:8]}"
        stream_buffer: list[str] = []
        streaming_active = {"value": False}

        async def on_stream_start() -> None:
            streaming_active["value"] = True
            await bridge.broadcast_stream_start(stream_id, source=source)
            await emit(f"\n{DEFAULT_THEME.assistant_label}")

        async def on_stream_token(token: str) -> None:
            stream_buffer.append(token)
            await bridge.broadcast_stream_delta(stream_id, token)
            # Live plain-text during stream (final Markdown rendered at end)
            sys.stdout.write(token)
            sys.stdout.flush()

        async def on_stream_end() -> None:
            streaming_active["value"] = False
            if stream_buffer:
                sys.stdout.write("\n")
                sys.stdout.flush()

        async def on_tool(tool_name: str, detail: str) -> None:
            label = tool_display_label(tool_name)
            activity = format_tool_activity_line(label, detail)
            await bridge.broadcast_tool_event(tool_name, "start", activity)
            await emit(f"[dim]  [cyan]›[/] {activity}[/dim]")

        llm_manager.set_tool_callback(on_tool)
        llm_manager.set_stream_callbacks(
            on_token=on_stream_token,
            on_start=on_stream_start,
            on_end=on_stream_end,
        )

        status_text = "[bold magenta]AXON is thinking...[/]"
        session_state["status"] = DEFAULT_THEME.status_thinking
        session_state["status_style"] = DEFAULT_THEME.accent

        from git_transactions import GitTransactionManager
        from autopilot_mode import is_autopilot_active
        from runtime_policy import load_runtime_policy

        policy = load_runtime_policy()
        use_git_tx = (is_autopilot_active() or policy.autonomy_enabled)
        tx = GitTransactionManager(Path.cwd())
        checkpoint = None

        if use_git_tx and tx.is_git:
            checkpoint = tx.create_checkpoint(f"before_agent_run_{uuid.uuid4().hex[:4]}")
            if checkpoint:
                await emit(f"[dim]  [cyan]✓[/] Transaction checkpoint created: {checkpoint[:8]}[/dim]\n")

        try:
            if background and not streaming_active["value"]:
                await emit(status_text)
            llm_manager.reload_credentials()
            result = await llm_manager.send_message_async(
                stripped,
                file_context=file_context,
            )
        except Exception as exc:
            if checkpoint:
                tx.rollback(checkpoint)
                await emit("[bold red]❌ Critical Agent crash! Transaction rolled back to last working checkpoint.[/]\n")
            raise exc
        finally:
            session_state["status"] = DEFAULT_THEME.status_ready
            session_state["status_style"] = DEFAULT_THEME.success
            llm_manager.set_stream_callbacks()

        if checkpoint:
            if result.ok:
                commit_msg = f"feat: AXON auto-commit - {stripped[:60]}"
                tx.finalize(checkpoint, commit_msg)
                await emit(f"[dim]  [green]✓[/] Git transaction committed: {commit_msg}[/dim]\n")
            else:
                tx.rollback(checkpoint)
                await emit("[bold red]❌ Agent failed to complete the task successfully. Transaction rolled back to last working checkpoint.[/]\n")

        full_text = result.content if result.ok else result.display_text
        await bridge.broadcast_stream_end(stream_id, full_text, source=source)

        if not streaming_active["value"] and not stream_buffer:
            await emit(f"\n{DEFAULT_THEME.assistant_label}")

        if result.ok and result.content:
            if not stream_buffer:
                await emit(Markdown(result.content, code_theme="monokai"))
        else:
            await emit(f"[red]{result.display_text}[/]")

        explore = get_turn_explore_summary()
        if explore:
            await emit(f"[dim]{explore}[/]")
            await bridge.broadcast(
                {"type": "explore_summary", "summary": explore},
            )

        await emit(
            f"\n[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n"
        )

        if result.usage:
            await sync_stats()
        if result.ok:
            from axon_notifications import notify_agent_complete
            msg = result.content or "The agent has completed the request."
            if len(msg) > 100:
                msg = msg[:97] + "..."
            notify_agent_complete("success", msg)
        else:
            from axon_notifications import notify_agent_complete
            msg = result.display_text or "The agent encountered an error."
            if len(msg) > 100:
                msg = msg[:97] + "..."
            notify_agent_complete("error", msg)
        return result

    async def run_plan_mode(description: str, *, background: bool = False) -> None:
        await emit(f"\n[bold cyan]❯ You:[/]\n/plan {description}")
        await emit("[bold magenta]📋 Entering Plan Mode — building task board...[/]")

        async with agent_slot():
            try:
                result = await llm_manager.send_plan_async(description)
                await emit("\n[bold green]✦ AXON:[/]")
                if result.ok and task_manager.has_plan():
                    if result.content:
                        await emit(Markdown(result.content))
                    await emit(
                        "[dim]Type [cyan]/execute[/] or [cyan]execute[/] to start the plan.[/dim]\n"
                    )
                else:
                    await emit(f"[red]{result.display_text}[/]")
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

        async with agent_slot():
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

    async def run_gen_skill(description: str, *, background: bool = False) -> None:
        if not description.strip():
            await emit(
                '[yellow]Usage: /gen-skill "description of the skill"[/]\n'
            )
            return

        await emit("\n[bold cyan]❯ You:[/]\n/gen-skill")
        await emit("[bold magenta]🛠 Generating skill with AI...[/]")

        async with agent_slot():
            result = await llm_manager.generate_skill_file_async(description.strip())

        if not result.ok:
            await emit(f"[red]{result.display_text}[/]\n")
            return

        try:
            path, skill_name = save_generated_skill_file(
                result.content,
                workspace=workspace,
            )
        except (OSError, ValueError) as exc:
            await emit(f"[red]Failed to save skill — {exc}[/]\n")
            return

        llm_manager.reload_skills()
        if result.usage:
            await sync_stats()

        await safe_async_print(
            f'[green][✓] Skill "{skill_name}" created and loaded successfully. '
            f"Use it with !{skill_name}.[/]\n"
        )

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

    async def run_create_agent() -> None:
        await emit("[bold magenta]🤖 Creating a new AXON sub-agent[/]\n")

        def _prompt_fields() -> tuple[str, str, str]:
            name = input("Agent name (e.g., code-reviewer): ").strip()
            focus = input("Specialty / focus: ").strip()
            mission = input("Mission (optional, Enter to skip): ").strip()
            return name, focus, mission

        app = get_app_or_none()
        if _prompt_is_active():
            name, focus, mission = await run_in_terminal(_prompt_fields)
        else:
            name, focus, mission = _prompt_fields()

        if not name:
            await emit("[red]Agent name is required.[/]\n")
            return
        if not focus:
            await emit("[red]Specialty/focus is required.[/]\n")
            return

        try:
            path = create_agent(name, focus, mission, workspace=workspace)
            await emit(
                f"[green][✓] Agent created![/] "
                f"Delegate with [cyan]/delegate {path.parent.name} <task>[/]\n"
            )
        except OSError as exc:
            await emit(f"[red]Failed to create agent — {exc}[/]\n")

    async def run_delegate(
        agent_name: str,
        task: str,
        *,
        background: bool = False,
    ) -> None:
        if not agent_name.strip():
            agents = list_agents(workspace)
            if agents:
                await emit(
                    "[yellow]Usage: /delegate <agent_name> <task>[/]\n"
                    f"[dim]Available: {', '.join(agents)}[/]\n"
                )
            else:
                await emit(
                    "[yellow]Usage: /delegate <agent_name> <task>[/]\n"
                    "[dim]No agents yet — use /create-agent[/]\n"
                )
            return

        if not task.strip():
            await emit("[yellow]Usage: /delegate <agent_name> <task>[/]\n")
            return

        await emit(
            f"\n[bold cyan]❯ Delegate →[/] [magenta]{agent_name}[/]\n{task}"
        )
        await emit(f"[bold magenta]🤖 Sub-agent {agent_name} working...[/]")

        display_text, file_context = build_file_context(task, workspace)

        async with agent_slot():
            result = await llm_manager.send_delegated_async(
                agent_name.strip(),
                display_text,
                file_context=file_context,
            )

        await emit(f"\n[bold green]✦ {agent_name}:[/]")
        if result.ok and result.content:
            await emit(Markdown(result.content))
        else:
            await emit(f"[red]{result.display_text}[/]")
        await emit(f"[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n")
        if result.usage:
            await sync_stats()

    async def run_multitask(stripped: str, *, background: bool = False) -> None:
        policy = load_runtime_policy()
        orch = Orchestrator(
            llm=llm_manager,
            workspace=workspace,
            allow_parallel=policy.allow_parallel_agents,
        )
        goal, agents = orch.parse_command(stripped)
        if not goal:
            await emit(
                "[yellow]Usage: /multitask [--agents name,name] <goal>[/]\n"
                "[dim]Example: /multitask review auth, add tests, update README[/]\n"
            )
            available = list_agents(workspace)
            if available:
                await emit(f"[dim]Agents: {', '.join(available)}[/]\n")
            return

        await emit(f"\n[bold cyan]❯ You:[/]\n{stripped}")
        await emit("[bold magenta]🎯 AXON Orchestrator — planning parallel work...[/]")
        if not policy.allow_parallel_agents:
            await emit(
                "[dim]Parallel agents disabled — running subtasks sequentially. "
                "Set allow_parallel_agents=true in runtime_policy.json to speed up.[/]\n"
            )
        if agents:
            await emit(f"[dim]Preferred agents: {', '.join(agents)}[/]\n")

        async def on_progress(message: str) -> None:
            await emit(message)

        def _subtask_payload(subtasks: list) -> list[dict[str, object]]:
            return [
                {
                    "id": task.id,
                    "title": task.title,
                    "agent": task.agent,
                    "status": task.status,
                }
                for task in subtasks
            ]

        async def on_multitask_event(
            phase: str,
            event_goal: str,
            subtasks: list,
            synthesis: str = "",
        ) -> None:
            await bridge.broadcast_multitask_update(
                phase,
                event_goal,
                _subtask_payload(subtasks),
                synthesis,
            )

        async with agent_slot():
            result = await orch.run(
                goal,
                preferred_agents=agents,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )

        if result.error and not result.synthesis:
            await emit(f"[red]{result.error}[/]\n")
            return

        llm_manager.messages.append(
            {"role": "user", "content": f"[Orchestrator multitask] {goal}"}
        )
        llm_manager.messages.append(
            {"role": "assistant", "content": result.synthesis or result.error or ""}
        )

        await emit(
            Panel(
                Markdown(result.synthesis or "(empty synthesis)"),
                title="🎯 Orchestrator Summary",
                border_style="cyan",
                padding=(0, 1),
            )
        )
        await emit(f"[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n")
        await sync_stats()
        from axon_notifications import notify_agent_complete
        status = "success" if not result.error else "error"
        msg = result.synthesis or result.error or "Orchestrator completed."
        if len(msg) > 100:
            msg = msg[:97] + "..."
        notify_agent_complete(status, msg)

    async def run_review(*, background: bool = False) -> None:
        prompt, error = build_review_prompt(workspace)
        if error:
            await emit(f"[red]{error}[/]\n")
            return

        await emit("\n[bold cyan]❯ You:[/]\n/review")
        await emit("[bold magenta]🔍 Reviewing git changes...[/]")

        async with agent_slot():
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

        async with agent_slot():
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

    async def run_artifacts(args: str = "") -> None:
        root = workspace / ".axon" / "artifacts"
        if not root.is_dir():
            await emit("[dim]No artifacts created in this project yet.[/]\n")
            return

        parts = args.split(maxsplit=1)
        action = parts[0].strip().lower() if parts else "list"

        if action == "view" and len(parts) > 1:
            filename = parts[1].strip()
            filename = Path(filename).name
            target = root / filename
            if not target.is_file():
                await emit(f"[red]Artifact '{filename}' not found.[/]\n")
                return
            try:
                content = target.read_text(encoding="utf-8", errors="replace")
                await emit(f"\n[bold cyan]--- Artifact: {filename} ---[/]\n{content}\n")
            except Exception as exc:
                await emit(f"[red]Failed to read artifact: {exc}[/]\n")
            return

        files = list(root.glob("*"))
        if not files:
            await emit("[dim]No artifacts created in this project yet.[/]\n")
            return

        await emit("\n[bold cyan]Project Artifacts:[/]\n")
        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
            size = f.stat().st_size
            import datetime
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            await emit(f"  [green]{f.name:<30}[/] ({size} bytes, modified {mtime})\n")
        await emit("\n[dim]Use `/artifacts view <filename>` to read an artifact's content.[/]\n")

    async def run_docs() -> None:
        candidates = [
            workspace / "scripts" / "docs_gen.py",
            install_root() / "scripts" / "docs_gen.py",
            bundle_root() / "scripts" / "docs_gen.py",
        ]
        script = next((path for path in candidates if path.is_file()), None)
        if script is None:
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
            await maybe_auto_save_session()
            await emit("[dim]AXON: Goodbye.[/dim]")
            shutdown.set()
            return True

        if cmd == "/help":
            lines = [
                f"  [cyan]{name:<14}[/] {desc}"
                for name, desc in merged_help_commands().items()
            ]
            await emit("[bold]AXON Commands[/bold]\n" + "\n".join(lines) + "\n")
            return True

        if await handle_config_command(stripped, emit=emit):
            return True

        if await handle_provider_command(stripped, emit=emit):
            return True

        if cmd == "/skills":
            from ui.skills_cmd import handle_skills_command
            if await handle_skills_command(stripped, llm_manager=llm_manager, emit=emit):
                return True

        if await handle_autopilot_command(stripped, emit=emit):
            return True

        if await try_plugin_command(stripped):
            return True

        if await handle_system_command(
            stripped,
            llm_manager=llm_manager,
            emit=emit,
            theme=DEFAULT_THEME,
        ):
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
            ok, detail = await llm_manager.compact_context()
            if ok:
                await emit(f"[green][✓] {detail}[/]\n")
                await persist_session()
            else:
                await emit(f"[yellow]{detail}[/]\n")
            return True

        if cmd == "/sessions":
            sessions = list_sessions()
            if not sessions:
                await emit("[dim]No saved sessions.[/]\n")
                return True
            lines = [
                f"  [cyan]{s.id}[/] {s.title[:50]} · {s.message_count} msgs · {s.updated_at[:19]}"
                for s in sessions[:20]
            ]
            await emit("[bold]Saved sessions[/bold]\n" + "\n".join(lines) + "\n")
            return True

        if cmd == "/resume":
            sid = args.strip()
            if not sid:
                await emit("[yellow]Usage: /resume <session_id>[/]\n")
                return True
            data = load_session(sid)
            if not data:
                await emit(f"[red]Session not found: {sid}[/]\n")
                return True
            llm_manager.messages = data.messages
            if data.meta.model:
                await apply_model(data.meta.model, background=background)
            current_session_id["id"] = data.meta.id
            await emit(f"[green][✓] Resumed session {sid} — {data.meta.title}[/]\n")
            return True

        if cmd == "/save":
            await persist_session(title=args.strip() or None)
            await emit(f"[green][✓] Session saved ({current_session_id['id']}).[/]\n")
            return True

        if cmd == "/export":
            from session_export import export_messages_markdown

            out_arg = args.strip()
            if out_arg:
                path = Path(out_arg).expanduser()
            else:
                path = None
            try:
                await persist_session()
                target = export_messages_markdown(
                    llm_manager.messages,
                    title=current_session_id["id"] or "AXON Session",
                    model=llm_manager.model,
                    tokens=TOTAL_TOKENS,
                    output=path,
                )
                await emit(f"[green][✓] Exported to {target}[/]\n")
            except OSError as exc:
                await emit(f"[red]Export failed — {exc}[/]\n")
            return True

        if cmd == "/login":
            from axon_auth import load_session, logout, run_login_flow, session_summary

            if args.strip().lower() == "force":
                logout()
            else:
                existing = load_session()
                if existing:
                    await emit(f"[green][✓] {session_summary()}[/]\n")
                    await emit(
                        "[dim]Use [cyan]/logout[/cyan] or [cyan]/login force[/cyan] to switch accounts.[/dim]\n"
                    )
                    return True

            await emit("[dim]Opening runaxon.xyz for sign-in…[/dim]\n")

            def _login() -> None:
                run_login_flow(open_browser=True)

            try:
                await asyncio.to_thread(_login)
            except RuntimeError as exc:
                await emit(f"[red]AXON: {exc}[/]\n")
                return True

            session = load_session()
            if session:
                await emit(f"[green][✓] Signed in as {session.email}[/]\n")
            return True

        if cmd == "/logout":
            from axon_auth import logout

            logout()
            await emit("[green][✓] Signed out.[/]\n")
            return True

        if cmd == "/mcp":
            parts = stripped.split(maxsplit=2)
            sub = (parts[1].lower() if len(parts) > 1 else "list")
            if sub == "list":
                servers = load_mcp_servers()
                if not servers:
                    await emit("[dim]No MCP servers configured.[/]\n")
                else:
                    lines = [
                        f"  [cyan]{s.name}[/] {'on' if s.enabled else 'off'} — {s.command} {' '.join(s.args)}"
                        for s in servers
                    ]
                    await emit("[bold]MCP servers[/bold]\n" + "\n".join(lines) + "\n")
            elif sub == "add" and len(parts) >= 3:
                rest = parts[2].strip()
                name, _, command_line = rest.partition(" ")
                if not name or not command_line:
                    await emit(
                        "[yellow]Usage: /mcp add <name> <command> [args...][/]\n"
                    )
                    return True
                cmd_parts = command_line.split()
                servers = load_mcp_servers()
                servers = [s for s in servers if s.name != name]
                servers.append(
                    McpServer(name=name, command=cmd_parts[0], args=cmd_parts[1:])
                )
                save_mcp_servers(servers)
                await emit(f"[green][✓] MCP server [cyan]{name}[/] saved.[/]\n")
            else:
                await emit(
                    "[yellow]Usage: /mcp list | /mcp add <name> <command>[/]\n"
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



        if cmd == "/export-skill":
            from ui.skill_export import export_skill

            name = args.strip()
            if not name:
                await emit("[yellow]Usage: /export-skill <name>[/]\n")
                return True
            try:
                dest = export_skill(name, workspace=workspace)
                await emit(f"[green][✓] Skill exported: {dest}[/]\n")
            except (OSError, ValueError) as exc:
                await emit(f"[red]{exc}[/]\n")
            return True

        if cmd == "/create-skill":
            await run_create_skill()
            return True

        if cmd == "/gen-skill":
            description = parse_gen_skill_description(stripped) or args
            await run_gen_skill(description, background=background)
            return True

        if cmd == "/review":
            await run_review(background=background)
            return True

        if cmd == "/undo":
            await run_undo()
            return True

        if cmd == "/artifacts":
            await run_artifacts(args)
            return True

        if cmd == "/commit":
            await run_commit(background=background)
            return True

        if cmd == "/docs":
            await run_docs()
            return True

        if cmd == "/create-agent":
            await run_create_agent()
            return True

        if cmd == "/delegate":
            parts = stripped.split(maxsplit=2)
            if len(parts) >= 3:
                await run_delegate(parts[1], parts[2], background=background)
            elif len(parts) == 2:
                await run_delegate(parts[1], "", background=background)
            else:
                await run_delegate("", "", background=background)
            return True

        if cmd == "/multitask":
            await run_multitask(stripped, background=background)
            return True

        if cmd == "/execute":
            await run_execute_mode(background=background)
            return True

        await emit(f"[yellow]AXON: Unknown command {cmd}. Type /help.[/]\n")
        return True

    async def handle_single_input(
        text: str,
        source: str = "terminal",
        *,
        background: bool | None = None,
    ) -> None:
        """Process one user input (slash command, plan, execute, or LLM message)."""
        if background is None:
            background = source == "web"

        stripped = text.strip()
        if not stripped:
            return

        policy = load_runtime_policy()
        if source == "web" and not policy.web_control_enabled:
            await emit(
                f"[red]Web control is disabled. Enable it at {config_url()}[/]\n"
            )
            return
        if source == "terminal" and not policy.terminal_control_enabled:
            await emit("[red]Terminal control is disabled in runtime policy.[/]\n")
            return

        source_token = set_request_source(source)
        try:
            await _handle_single_input_body(
                text,
                source,
                background=background,
                stripped=stripped,
            )
        finally:
            reset_request_source(source_token)

    async def _handle_single_input_body(
        text: str,
        source: str,
        *,
        background: bool,
        stripped: str,
    ) -> None:
        if stripped.lower().startswith("/plan"):
            description = stripped[5:].strip()
            if description:
                await run_plan_mode(description, background=background)
            else:
                await emit("[yellow]Usage: /plan <description>[/]\n")
            return

        if stripped.lower().startswith("/multitask"):
            await run_multitask(stripped, background=background)
            return

        if not stripped.startswith("/"):
            intent = detect_intent(
                stripped, has_active_plan=task_manager.has_plan()
            )
            if intent == "multitask":
                await run_multitask(stripped, background=background)
                return
            if intent == "plan":
                await run_plan_mode(stripped, background=background)
                return
            if intent == "execute":
                await run_execute_mode(background=background)
                return

        if stripped.startswith("/"):
            if stripped.lower().startswith("/delegate"):
                parts = stripped.split(maxsplit=2)
                agent = parts[1] if len(parts) > 1 else ""
                task = parts[2] if len(parts) > 2 else ""
                await run_delegate(agent, task, background=background)
                return
            await execute_slash_command(stripped, background=background)
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

        quick_reply = try_chitchat_reply(stripped) if not file_context else None
        if quick_reply:
            llm_manager.messages.append({"role": "user", "content": stripped})
            llm_manager.messages.append({"role": "assistant", "content": quick_reply})
            await emit(f"\n{DEFAULT_THEME.assistant_label}")
            await emit(quick_reply)
            await emit(
                f"\n[dim]Cost: ${TOTAL_COST:.4f} | Tokens: {TOTAL_TOKENS}[/dim]\n"
            )
            await bridge.broadcast_chat(
                role="assistant",
                text=quick_reply,
                source=source,
                message_id=f"{source}-axon-{uuid.uuid4().hex[:8]}",
            )
            return

        async with agent_slot():
            try:
                result = await run_llm(
                    stripped,
                    background=background,
                    file_context=file_context,
                    source=source,
                )
            except Exception as exc:
                error_text = f"[ERROR]: {exc}"
                await emit(f"\n[bold red]✦ AXON:[/] {error_text}\n")
                await bridge.broadcast_chat(
                    role="assistant",
                    text=error_text,
                    source=source,
                )

    async def process_user_message(text: str, source: str = "terminal") -> None:
        background = source == "web"

        async def _handle() -> None:
            stripped = text.strip()
            if not stripped:
                return

            if is_command_chain(stripped):
                parts = split_command_chain(stripped)
                await emit(
                    f"[dim]⛓ Running {len(parts)} chained commands…[/]\n"
                )
                for index, part in enumerate(parts, start=1):
                    await emit(f"[dim]── Chain {index}/{len(parts)} ──[/]")
                    await handle_single_input(
                        part,
                        source,
                        background=background,
                    )
                return

            await handle_single_input(text, source, background=background)

        if background:
            async with in_terminal():
                background_render["active"] = True
                try:
                    await _handle()
                finally:
                    background_render["active"] = False
        else:
            await _handle()

    def cancel_active_generation():
        task = active_generation.get("task")
        if task and not task.done():
            task.cancel()
            active_generation["task"] = None

    bridge.configure(
        process_chat=process_user_message,
        set_model=lambda model: apply_model(
            model, announce_cli=True, background=True
        ),
        refresh_ui=lambda: None,
        current_model=llm_manager.model,
        cancel_chat=cancel_active_generation,
    )

    ws_server = await bridge.start()

    async def stats_heartbeat() -> None:
        tick = 0
        while not shutdown.is_set():
            await asyncio.sleep(10)
            await sync_stats()
            tick += 1
            if tick % 30 == 0:
                with contextlib.suppress(Exception):
                    await persist_session()

    heartbeat_task = asyncio.create_task(stats_heartbeat())

    if not headless:
        clear_terminal()
        print_banner(llm_manager.model, workspace)

    runtime = load_runtime_policy()
    from autopilot_mode import is_autopilot_active, is_process_elevated

    autopilot_line = ""
    if runtime.autopilot_enabled or is_autopilot_active():
        autopilot_state = "ON" if is_autopilot_active() else "armed (need admin)"
        autopilot_line = f" · autopilot [cyan]{autopilot_state}[/cyan]"

    if not headless:
        console.print(
            f"[dim]Bridge ws://127.0.0.1:8765 · PIN [cyan]{runtime.bridge_pin}[/cyan] · "
            f"autonomy [cyan]{'on' if runtime.autonomy_enabled else 'off'}[/cyan] · "
            f"web [cyan]{'on' if runtime.web_control_enabled else 'off'}[/cyan]"
            f"{autopilot_line}[/dim]"
        )
        if runtime.autopilot_enabled and not is_process_elevated():
            console.print(
                "[yellow]Autopilot is enabled in policy but this terminal is not elevated — "
                "run as Administrator or use /autopilot off.[/yellow]"
            )
        if has_bundled_zenith():
            console.print(
                f"[dim]Control panel: [cyan]{panel_url()}[/cyan] · "
                f"settings: [cyan]{config_url()}[/cyan][/dim]"
            )
            if not is_llm_configured():
                console.print(
                    f"[yellow]LLM not configured — {provider_config_hint()}[/yellow]"
                )
            console.print(
                "[dim]If the panel is not open yet, run [cyan]axon web --open[/cyan] in another terminal.[/dim]\n"
            )
        else:
            console.print(
                f"[dim]Control panel: [cyan]{panel_url()}[/cyan] · "
                f"start with [cyan]axon web --open[/cyan][/dim]\n"
            )

    async def chat_loop() -> None:
        while not shutdown.is_set():
            try:
                with patch_stdout():
                    user_input = await session.prompt_async([("class:prompt", "❯ ")])
            except KeyboardInterrupt:
                if active_generation["task"] and not active_generation["task"].done():
                    llm_manager.request_cancel()
                    active_generation["task"].cancel()
                    await emit("[dim]Generation cancelled.[/dim]\n")
                    active_generation["task"] = None
                    continue
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

            if stripped.lower().startswith("/artifacts"):
                args = stripped[10:].strip()
                await run_artifacts(args)
                if shutdown.is_set():
                    break
                continue

            if stripped.lower() == "/commit":
                await run_commit()
                if shutdown.is_set():
                    break
                continue

            if is_command_chain(stripped):
                parts = split_command_chain(stripped)
                await emit(f"[dim]⛓ Running {len(parts)} chained commands…[/]\n")
                for index, part in enumerate(parts, start=1):
                    await emit(f"[dim]── Chain {index}/{len(parts)} ──[/]")
                    await handle_single_input(part, "terminal")
                    if shutdown.is_set():
                        break
                if shutdown.is_set():
                    break
                continue

            if stripped.startswith("/"):
                await execute_slash_command(stripped)
                if shutdown.is_set():
                    break
                continue

            async def _run() -> None:
                await process_user_message(user_input, "terminal")

            task = asyncio.create_task(_run())
            active_generation["task"] = task
            try:
                await task
            except asyncio.CancelledError:
                pass
            finally:
                active_generation["task"] = None
            if shutdown.is_set():
                break

    try:
        if headless:
            while not shutdown.is_set():
                await asyncio.sleep(0.5)
        else:
            await chat_loop()
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task
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
