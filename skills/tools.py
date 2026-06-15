from __future__ import annotations

import json
import shlex
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from backup_manager import backup_manager
from rich.panel import Panel
from rich.text import Text

ApprovalDecision = Literal["once", "session", "deny"]
ApprovalCallback = Callable[[str, str], Awaitable[ApprovalDecision]]
ToolResultCallback = Callable[[str, str, str], Awaitable[None]]

MAX_FILE_SIZE = 64 * 1024
SHELL_TIMEOUT_SECONDS = 60
MAX_PANEL_OUTPUT = 4000

REQUIRES_APPROVAL = frozenset({"write_file", "execute_shell"})

# Tool names (or "tool:detail" prefixes) approved for the rest of the CLI session.
approved_session_tools: set[str] = set()

_on_tool_result: ToolResultCallback | None = None

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read and return the text content of a file at the given path. "
                "Use for inspecting source code, configs, or logs."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Absolute or relative path to the file to read.",
                    },
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write text content to a file. Creates parent directories if needed. "
                "Requires user approval before running."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write into the file.",
                    },
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": (
                "Execute a shell command and return combined stdout/stderr. "
                "Requires user approval before running."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current events, fresh documentation, or facts "
                "not in training data. Returns top results with titles and snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


def get_tools_schema() -> list[dict[str, Any]]:
    return TOOL_SCHEMAS


def clear_session_approvals() -> None:
    """Reset session-scoped tool permissions (e.g. on /clear)."""
    approved_session_tools.clear()


def set_tool_result_callback(callback: ToolResultCallback | None) -> None:
    global _on_tool_result
    _on_tool_result = callback


def session_approval_key(tool_name: str, detail: str = "") -> str:
    """Key used for session-level approval bypass."""
    if tool_name == "execute_shell" and detail.strip():
        return f"{tool_name}:{detail.strip()}"
    return tool_name


def is_session_approved(tool_name: str, detail: str = "") -> bool:
    if tool_name in approved_session_tools:
        return True
    if detail.strip():
        return session_approval_key(tool_name, detail) in approved_session_tools
    return False


def grant_session_approval(tool_name: str, detail: str = "") -> None:
    """Remember approval for the tool category for the rest of the session."""
    approved_session_tools.add(tool_name)
    _ = detail  # reserved for future command-prefix scoping


def tool_display_label(tool_name: str) -> str:
    builtin = {
        "execute_shell": "Shell",
        "write_file": "Write",
        "read_file": "Read",
        "web_search": "Search",
        "create_plan": "Plan",
        "complete_task": "Task",
        "update_task_status": "Task",
    }
    if tool_name in builtin:
        return builtin[tool_name]
    return f"Skill:{tool_name}"


def build_permission_panel(tool_name: str, detail: str) -> Panel:
    label = tool_display_label(tool_name)
    display_detail = detail.strip() or "(no details)"

    body = Text()
    body.append(f"Allow execution of [{label}]?\n\n", style="bold")
    body.append("1. Allow once\n", style="green")
    body.append("2. Allow for this session\n", style="yellow")
    body.append("3. No, reject\n", style="red")

    return Panel(
        body,
        title=f"[?] {label}: {display_detail}",
        border_style="yellow",
        padding=(0, 1),
    )


def build_rejection_panel(tool_name: str, detail: str) -> Panel:
    label = tool_display_label(tool_name)
    display_detail = detail.strip() or "(no details)"
    return Panel(
        Text("Permission denied by user.", style="bold red"),
        title=f"[✗] {label}: {display_detail}",
        border_style="red",
        padding=(0, 1),
    )


def build_result_panel(tool_name: str, detail: str, output: str) -> Panel:
    label = tool_display_label(tool_name)
    display_detail = detail.strip() or "(no details)"
    body = output if output else "(no output)"
    if len(body) > MAX_PANEL_OUTPUT:
        body = f"{body[:MAX_PANEL_OUTPUT]}\n\n… [truncated for display]"

    if tool_name == "execute_shell":
        title = f"[✓] Shell {display_detail}"
    elif tool_name == "write_file":
        title = f"[✓] Write {display_detail}"
    else:
        title = f"[✓] {label} {display_detail}"

    return Panel(
        body,
        title=title,
        border_style="green",
        padding=(0, 1),
    )


def _resolve_safe_path(filepath: str) -> Path | str:
    raw = filepath.strip()
    if not raw:
        return "Error: filepath is required."

    if ".." in Path(raw).parts:
        return "Error: path traversal ('..') is not allowed."

    try:
        return Path(raw).resolve()
    except (OSError, ValueError) as exc:
        return f"Error: invalid path — {exc}"


def read_file(filepath: str) -> str:
    """Read and return file content."""
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    if not path.is_file():
        return f"Error: file not found — {path}"

    try:
        size = path.stat().st_size
        text = path.read_text(encoding="utf-8", errors="replace")
        if size > MAX_FILE_SIZE:
            return (
                f"{text[:MAX_FILE_SIZE]}\n\n"
                f"[Truncated: file is {size} bytes, "
                f"showing first {MAX_FILE_SIZE} bytes]"
            )
        return text
    except OSError as exc:
        return f"Error: could not read file — {exc}"


def write_file(filepath: str, content: str) -> str:
    """Write content to a file."""
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    try:
        backup_manager.set_workspace(Path.cwd())
        backup_path = backup_manager.backup_if_exists(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if backup_path:
            return (
                f"Successfully wrote {len(content)} characters to {path} "
                f"(backup: {backup_path.name})"
            )
        return f"Successfully wrote {len(content)} characters to {path}"
    except OSError as exc:
        return f"Error: could not write file — {exc}"


def web_search(query: str) -> str:
    """Search the web via DuckDuckGo and return formatted top results."""
    q = query.strip()
    if not q:
        return "Error: search query is required."

    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return (
            "Error: duckduckgo-search is not installed. "
            "Run: pip install duckduckgo-search"
        )

    try:
        lines: list[str] = []
        with DDGS() as ddgs:
            results = list(ddgs.text(q, max_results=5))
        if not results:
            return f"No web results found for: {q}"

        for index, item in enumerate(results, start=1):
            title = item.get("title") or "(no title)"
            href = item.get("href") or item.get("link") or ""
            body = item.get("body") or item.get("snippet") or ""
            lines.append(f"{index}. {title}\n   {href}\n   {body}")

        return f"Web search results for '{q}':\n\n" + "\n\n".join(lines)
    except Exception as exc:
        return f"Error during web search — {exc}"


def execute_shell(command: str) -> str:
    """Execute a shell command and return stdout/stderr."""
    cmd = command.strip()
    if not cmd:
        return "Error: command is required."

    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )
        else:
            proc = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )

        parts: list[str] = []
        if proc.stdout:
            parts.append(proc.stdout)
        if proc.stderr:
            parts.append(proc.stderr)

        output = "\n".join(parts).strip()
        if output:
            return f"{output}\n[exit code {proc.returncode}]"
        return f"(no output, exit code {proc.returncode})"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {SHELL_TIMEOUT_SECONDS} seconds"
    except Exception as exc:
        return f"Error executing command — {exc}"


def _approval_detail(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name == "execute_shell":
        return str(args.get("command", "")).strip()
    if tool_name == "write_file":
        return str(args.get("filepath", "")).strip()
    return json.dumps(args, ensure_ascii=False)[:120]


def _run_tool_sync(tool_name: str, args: dict[str, Any]) -> str:
    if tool_name == "read_file":
        return read_file(str(args.get("filepath", "")))
    if tool_name == "write_file":
        return write_file(
            str(args.get("filepath", "")),
            str(args.get("content", "")),
        )
    if tool_name == "execute_shell":
        return execute_shell(str(args.get("command", "")))
    if tool_name == "web_search":
        return web_search(str(args.get("query", "")))
    return f"Error: unknown tool '{tool_name}'."


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    approve: ApprovalCallback | None = None,
) -> str:
    """Dispatch a tool call, requesting approval for dangerous operations."""
    detail = _approval_detail(tool_name, arguments)

    if tool_name in REQUIRES_APPROVAL and not is_session_approved(tool_name, detail):
        if approve is None:
            return "User denied permission (no approval handler configured)"
        decision = await approve(tool_name, detail)
        if decision == "deny":
            return "User denied permission"
        if decision == "session":
            grant_session_approval(tool_name, detail)

    result = _run_tool_sync(tool_name, arguments)

    if tool_name in REQUIRES_APPROVAL and _on_tool_result is not None:
        await _on_tool_result(tool_name, detail, result)

    return result


def parse_tool_arguments(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}
