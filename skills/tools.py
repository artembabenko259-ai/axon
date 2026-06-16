from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, Literal

from audit_log import log_tool_event, scan_secrets
from backup_manager import backup_manager
from request_context import get_request_source
from runtime_policy import load_runtime_policy
from rich.panel import Panel
from rich.text import Text
from ui.explore_stats import record_explore_tool

ApprovalDecision = Literal["once", "session", "deny"]
ApprovalCallback = Callable[[str, str], Awaitable[ApprovalDecision]]
ToolResultCallback = Callable[[str, str, str], Awaitable[None]]

MAX_FILE_SIZE = 64 * 1024
SHELL_TIMEOUT_SECONDS = 60
MAX_PANEL_OUTPUT = 4000
_READ_FILE_CACHE: dict[str, tuple[float, int, int]] = {}

SHELL_DENY_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-rf", "recursive force delete"),
    (r"\bformat\s+[a-z]:", "disk format"),
    (r"del\s+/f", "forced delete"),
    (r"Remove-Item\s+.+-Recurse\s+-Force", "PowerShell recursive delete"),
]

REQUIRES_APPROVAL = frozenset({"write_file", "execute_shell", "apply_patch"})

IGNORE_DIR_NAMES = frozenset(
    {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".axon"}
)
MAX_GLOB_RESULTS = 200
MAX_SEARCH_RESULTS = 100

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
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List files and directories at a path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path."},
                    "recursive": {
                        "type": "boolean",
                        "description": "List recursively (max depth 4).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob_files",
            "description": "Find files matching a glob pattern under a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern, e.g. **/*.py",
                    },
                    "path": {
                        "type": "string",
                        "description": "Root directory to search from.",
                    },
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a regex pattern in codebase files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern."},
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search.",
                    },
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": (
                "Apply a unified diff patch to a file. Requires user approval."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Target file path."},
                    "patch": {
                        "type": "string",
                        "description": "Unified diff hunk(s) for the file.",
                    },
                },
                "required": ["filepath", "patch"],
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
        "list_dir": "List",
        "glob_files": "Glob",
        "search_code": "Grep",
        "apply_patch": "Edit",
        "web_search": "Search",
        "create_plan": "Plan",
        "complete_task": "Task",
        "update_task_status": "Task",
    }
    if tool_name in builtin:
        return builtin[tool_name]
    return f"Skill:{tool_name}"


def _truncate_activity(text: str, max_len: int = 96) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_len:
        return compact
    return f"{compact[: max_len - 1]}…"


def _display_path(raw: str) -> str:
    """Cursor-style @path (relative to cwd when possible)."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        return raw
    try:
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        else:
            path = path.resolve()
        cwd = Path.cwd().resolve()
        if path == cwd:
            return "@."
        try:
            rel = path.relative_to(cwd)
            return f"@{rel.as_posix()}"
        except ValueError:
            return f"@{path.as_posix()}"
    except OSError:
        return f"@{raw}"


def _quote_activity(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return '""'
    if " " in text or '"' in text:
        escaped = text.replace('"', '\\"')
        return f'"{escaped}"'
    return text


def tool_activity_detail(tool_name: str, args: dict[str, Any]) -> str:
    """Human-readable target for approvals, bridge events, and activity feeds."""
    if tool_name == "execute_shell":
        return _truncate_activity(str(args.get("command", "")))
    if tool_name in {"read_file", "write_file", "apply_patch"}:
        return _display_path(str(args.get("filepath", "")))
    if tool_name == "list_dir":
        path = _display_path(str(args.get("path", ".")))
        if args.get("recursive"):
            return f"{path} (recursive)" if path else "(recursive)"
        return path or "@."
    if tool_name == "glob_files":
        pattern = str(args.get("pattern", "")).strip() or "*"
        root = _display_path(str(args.get("path", "."))) or "@."
        return f"{pattern} in {root}"
    if tool_name == "search_code":
        pattern = _quote_activity(str(args.get("pattern", "")))
        root = _display_path(str(args.get("path", "."))) or "@."
        return f"{pattern} in {root}"
    if tool_name == "web_search":
        return _quote_activity(str(args.get("query", "")))
    if tool_name == "create_plan":
        goal = str(args.get("goal", "")).strip()
        tasks = args.get("tasks") or []
        count = len(tasks) if isinstance(tasks, list) else 0
        if goal:
            return _truncate_activity(f"{_quote_activity(goal)} ({count} steps)")
        return f"{count} steps"
    if tool_name == "complete_task":
        task_id = args.get("task_id", args.get("id", ""))
        return f"#{task_id}" if task_id != "" else ""
    if tool_name == "update_task_status":
        task_id = args.get("task_id", args.get("id", ""))
        status = str(args.get("status", "")).strip()
        if task_id != "" and status:
            return f"#{task_id} → {status}"
        if task_id != "":
            return f"#{task_id}"
        return status
    # plugin / unknown tools — show first string arg if any
    for value in args.values():
        if isinstance(value, str) and value.strip():
            return _truncate_activity(value.strip())
    return _truncate_activity(json.dumps(args, ensure_ascii=False))


def format_tool_activity(tool_name: str, args: dict[str, Any]) -> str:
    """Cursor / Claude Code style line, e.g. 'Read @ui/repl.py'."""
    label = tool_display_label(tool_name)
    detail = tool_activity_detail(tool_name, args)
    return format_tool_activity_line(label, detail)


def format_tool_activity_line(label: str, detail: str = "") -> str:
    detail = (detail or "").strip()
    if detail:
        return f"{label} {detail}"
    return label


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


def _is_path_allowed(path: Path) -> bool:
    try:
        cwd = Path.cwd().resolve()
        resolved = path.resolve()
        return resolved == cwd or cwd in resolved.parents
    except OSError:
        return False


def _resolve_safe_path(filepath: str) -> Path | str:
    raw = filepath.strip()
    if not raw:
        return "Error: filepath is required."

    if ".." in Path(raw).parts:
        return "Error: path traversal ('..') is not allowed."

    try:
        path = Path(raw).resolve()
    except (OSError, ValueError) as exc:
        return f"Error: invalid path — {exc}"

    if not _is_path_allowed(path):
        return f"Error: path outside workspace — {path}"

    return path


def clear_read_file_cache() -> None:
    """Drop cached file reads (new user turn / session reset)."""
    _READ_FILE_CACHE.clear()


def read_file(filepath: str) -> str:
    """Read and return file content."""
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    if not path.is_file():
        return f"Error: file not found — {path}"

    try:
        stat = path.stat()
        size = stat.st_size
        cache_key = str(path)
        cached = _READ_FILE_CACHE.get(cache_key)
        if cached and cached[0] == stat.st_mtime and cached[1] == size:
            line_count = cached[2]
            return (
                f"[Cached — {path.name} unchanged, {size} bytes, ~{line_count} lines. "
                "Content is already in context from the previous read; "
                "only read again if the file may have changed.]"
            )

        text = path.read_text(encoding="utf-8", errors="replace")
        line_count = text.count("\n") + (1 if text else 0)
        _READ_FILE_CACHE[cache_key] = (stat.st_mtime, size, line_count)

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
    secrets = scan_secrets(content)
    if secrets:
        return f"Error: blocked write — possible secrets detected: {', '.join(secrets)}"

    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    try:
        backup_manager.set_workspace(Path.cwd())
        backup_path = backup_manager.backup_if_exists(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        _READ_FILE_CACHE.pop(str(path.resolve()), None)
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
        from ddgs import DDGS
    except ImportError:
        return "Error: ddgs is not installed. Run: pip install ddgs"

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


def list_dir(path: str, recursive: bool = False) -> str:
    root = _resolve_safe_path(path)
    if isinstance(root, str):
        return root
    if not root.is_dir():
        return f"Error: not a directory — {root}"

    lines: list[str] = []

    def _walk(directory: Path, depth: int) -> None:
        if depth > 4:
            return
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            lines.append(f"Error reading {directory}: {exc}")
            return
        for entry in entries:
            if entry.name in IGNORE_DIR_NAMES:
                continue
            prefix = "  " * depth
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{prefix}{entry.name}{suffix}")
            if recursive and entry.is_dir():
                _walk(entry, depth + 1)

    _walk(root, 0)
    return "\n".join(lines) if lines else "(empty directory)"


def glob_files(pattern: str, path: str) -> str:
    root = _resolve_safe_path(path)
    if isinstance(root, str):
        return root
    if not root.is_dir():
        return f"Error: not a directory — {root}"

    try:
        matches = sorted(root.glob(pattern))[:MAX_GLOB_RESULTS]
    except (OSError, ValueError) as exc:
        return f"Error: invalid glob — {exc}"

    if not matches:
        return f"No files matched '{pattern}' under {root}"

    lines = [str(p.relative_to(root)) for p in matches]
    note = ""
    if len(matches) >= MAX_GLOB_RESULTS:
        note = f"\n[truncated at {MAX_GLOB_RESULTS} results]"
    return "\n".join(lines) + note


def search_code(pattern: str, path: str) -> str:
    target = _resolve_safe_path(path)
    if isinstance(target, str):
        return target

    rg = shutil.which("rg")
    if rg:
        cmd = [rg, "-n", "--no-heading", "-S", pattern, str(target)]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )
            output = (proc.stdout or "").strip()
            if not output:
                return f"No matches for /{pattern}/ in {target}"
            lines = output.splitlines()[:MAX_SEARCH_RESULTS]
            body = "\n".join(lines)
            if len(output.splitlines()) > MAX_SEARCH_RESULTS:
                body += f"\n[truncated at {MAX_SEARCH_RESULTS} matches]"
            return body
        except (subprocess.TimeoutExpired, OSError) as exc:
            return f"Error running ripgrep — {exc}"

    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Error: invalid regex — {exc}"

    matches: list[str] = []
    files = [target] if target.is_file() else target.rglob("*")
    for file_path in files:
        if not file_path.is_file():
            continue
        if any(part in IGNORE_DIR_NAMES for part in file_path.parts):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                try:
                    rel = file_path.relative_to(Path.cwd())
                except ValueError:
                    rel = file_path
                matches.append(f"{rel}:{line_no}:{line[:200]}")
                if len(matches) >= MAX_SEARCH_RESULTS:
                    return "\n".join(matches) + f"\n[truncated at {MAX_SEARCH_RESULTS} matches]"
    return "\n".join(matches) if matches else f"No matches for /{pattern}/ in {target}"


def apply_patch(filepath: str, patch: str) -> str:
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    if not path.is_file():
        return f"Error: file not found — {path}"

    original = path.read_text(encoding="utf-8", errors="replace")
    lines = original.splitlines(keepends=True)
    patch_text = patch.replace("\r\n", "\n")

    ops: list[tuple[str, str]] = []
    for raw in patch_text.splitlines():
        if raw.startswith("@@") or raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw and raw[0] in " -+":
            ops.append((raw[0], raw[1:]))

    out: list[str] = []
    src_i = 0
    src = [ln.rstrip("\n") for ln in lines]
    for op, text in ops:
        if op == " ":
            if src_i < len(src) and src[src_i] == text:
                out.append(src[src_i] + "\n")
                src_i += 1
            elif src_i < len(src):
                return f"Error: context mismatch at line {src_i + 1}"
            else:
                out.append(text + "\n")
        elif op == "-":
            if src_i < len(src) and src[src_i] == text:
                src_i += 1
            else:
                return f"Error: delete mismatch at line {src_i + 1}"
        elif op == "+":
            out.append(text + "\n")
    out.extend(ln + "\n" for ln in src[src_i:])

    backup_manager.set_workspace(Path.cwd())
    backup_manager.backup_if_exists(path)
    path.write_text("".join(out), encoding="utf-8")
    _READ_FILE_CACHE.pop(str(path.resolve()), None)
    return f"Successfully patched {path}"


def execute_shell(command: str) -> str:
    """Execute a shell command and return stdout/stderr."""
    cmd = command.strip()
    if not cmd:
        return "Error: command is required."

    for pattern, label in SHELL_DENY_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return f"Error: blocked command pattern ({label})"

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
    return tool_activity_detail(tool_name, args)


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
    if tool_name == "list_dir":
        return list_dir(str(args.get("path", ".")), bool(args.get("recursive", False)))
    if tool_name == "glob_files":
        return glob_files(str(args.get("pattern", "")), str(args.get("path", ".")))
    if tool_name == "search_code":
        return search_code(str(args.get("pattern", "")), str(args.get("path", ".")))
    if tool_name == "apply_patch":
        return apply_patch(
            str(args.get("filepath", "")),
            str(args.get("patch", "")),
        )
    return f"Error: unknown tool '{tool_name}'."


def _needs_approval(tool_name: str) -> bool:
    from openclaw_mode import is_openclaw_active

    policy = load_runtime_policy()
    if is_openclaw_active() or policy.autonomy_enabled:
        return False
    mode = policy.tool_mode(tool_name)
    if mode == "auto":
        return False
    if mode == "deny":
        return True
    return tool_name in REQUIRES_APPROVAL


async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    approve: ApprovalCallback | None = None,
) -> str:
    """Dispatch a tool call, requesting approval for dangerous operations."""
    policy = load_runtime_policy()
    if policy.tool_mode(tool_name) == "deny":
        return f"Error: tool '{tool_name}' is denied by runtime policy."

    detail = _approval_detail(tool_name, arguments)

    if _needs_approval(tool_name) and not is_session_approved(tool_name, detail):
        if approve is None:
            return "User denied permission (no approval handler configured)"
        decision = await approve(tool_name, detail)
        if decision == "deny":
            log_tool_event(
                tool=tool_name,
                detail=detail,
                source=get_request_source(),
                outcome="denied",
            )
            return "User denied permission"
        if decision == "session":
            grant_session_approval(tool_name, detail)

    result = _run_tool_sync(tool_name, arguments)
    record_explore_tool(tool_name, detail)

    log_tool_event(
        tool=tool_name,
        detail=detail,
        source=get_request_source(),
        outcome="ok" if not result.startswith("Error") else "error",
    )

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
