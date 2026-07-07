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
            "name": "search_semantic",
            "description": (
                "Search the workspace code semantic index using natural language queries to locate relevant files and code blocks."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query describing what code you want to find (e.g. 'auth logic', 'websocket port').",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_dependencies",
            "description": (
                "Locate all references, imports, and usages of a specific class or function symbol across the codebase to ensure consistent refactoring."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "The exact name of the function, class, struct, or variable to find references for.",
                    },
                },
                "required": ["symbol"],
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
            "name": "take_screenshot",
            "description": (
                "Capture the full screen when YOU need visual confirmation — GUI state, "
                "dialogs, browser windows, app results. Call only when seeing the screen "
                "is necessary to continue; do not use after every shell command. "
                "With a vision model, the image is attached to your context automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "purpose": {
                        "type": "string",
                        "description": (
                            "What you want to verify on screen (e.g. 'login dialog closed')."
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": "Optional filename (default: screenshot-TIMESTAMP.png)",
                    },
                },
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
            "name": "search_symbol",
            "description": "Find where a class, function, or method is defined in the workspace using indexed AST.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Name of the class, function, or method (case-insensitive substring)."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_codebase_map",
            "description": "Retrieve a map of all files, classes, and functions in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_webpage",
            "description": "Fetch the clean text contents of a webpage URL (e.g. for reading documentation).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL starting with http or https."}
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "inspect_image",
            "description": "Load and inspect a local image file (PNG, JPG, etc.) into the vision context to analyze its visual contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the local image file."},
                    "purpose": {"type": "string", "description": "What you want to verify or look for in the image (optional)."}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "deep_search",
            "description": "Perform multi-step research on a query: searches the web, reads top pages, and synthesizes a detailed report.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search or research query."}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_syntax",
            "description": "Verify python file syntax using AST parser to catch syntax errors immediately.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Path to the python file to validate."}
                },
                "required": ["filepath"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_status",
            "description": "Get git status summary showing modified, deleted, or untracked files.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "git_diff",
            "description": "Get current unstaged diff changes in the git repository.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_memory",
            "description": "Store a long-term project fact or lesson learned in the project memory (.axon/memory.md) for future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category of information (e.g., 'setup', 'architecture', 'guideline')."},
                    "key": {"type": "string", "description": "Short identifier key for the fact (e.g. 'npm_run_dev_issue')."},
                    "value": {"type": "string", "description": "The detailed fact, setting, or learning to remember."}
                },
                "required": ["category", "key", "value"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_artifact",
            "description": "Create or update a structured user-facing artifact document (e.g., plans, specifications, reports) in .axon/artifacts/.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Artifact filename (e.g., 'system_architecture.md', 'plan_log.md')."},
                    "content": {"type": "string", "description": "Full markdown content of the artifact."},
                    "summary": {"type": "string", "description": "Brief, human-readable summary of what this artifact contains."}
                },
                "required": ["filename", "content", "summary"]
            }
        }
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
    {
        "type": "function",
        "function": {
            "name": "schedule",
            "description": (
                "Schedule a daily cron task or a one-shot delay timer to run a prompt/task. "
                "For daily/recurring tasks, specify 'cron' with hour and minute. "
                "For one-shot timers, specify 'duration_seconds'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The AXON command or prompt to run when triggered.",
                    },
                    "cron": {
                        "type": "string",
                        "description": "Optional recurring cron expression, e.g. '0 9 * * *' for daily at 9:00 AM, or '*/5 * * * *' for every 5 mins.",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Optional delay in seconds for a one-shot timer.",
                    },
                    "timer_condition": {
                        "type": "string",
                        "description": "Optional condition to cancel the timer early: 'never', 'any', or a specific task_id.",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Optional directory path to execute the command in.",
                    },
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_task",
            "description": (
                "Manage background tasks in the queue or scheduler. "
                "Actions: 'list' (list running/pending tasks), 'kill' (cancel/remove a task or timer), "
                "'status' (get details of a task by ID), 'send_input' (send standard input to a running task)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "kill", "status", "send_input"],
                        "description": "Action to perform on the background tasks.",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "The unique ID of the target task, scheduled task, or timer.",
                    },
                    "input_text": {
                        "type": "string",
                        "description": "Input to send to the task's stdin (used when action is 'send_input').",
                    },
                },
                "required": ["action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decompile_file",
            "description": "AXON Dart: Decompile native C/C++ binaries, Java class/jar files, or C#/.NET assembly files to C-like pseudo-code or intermediate representations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the target executable, DLL, class, or JAR file.",
                    },
                    "symbol_name": {
                        "type": "string",
                        "description": "Optional name of the specific function or method to decompile (primarily for native C/C++ targets).",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_subagent",
            "description": "Defines a new type of subagent with a specialized system prompt, description, and role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique identifier/name for the subagent type (e.g. 'DatabaseOptimizer', 'SecurityAuditor').",
                    },
                    "system_prompt": {
                        "type": "string",
                        "description": "Detailed system prompt instructions for this subagent.",
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this subagent specializes in.",
                    },
                },
                "required": ["name", "system_prompt", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_subagent",
            "description": "Spawns a subagent to run a specific task in the background.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the subagent type to invoke (either a newly defined name or a standard agent name).",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Actionable task description or prompt for the subagent.",
                    },
                    "workspace_mode": {
                        "type": "string",
                        "enum": ["inherit", "branch", "share"],
                        "description": "Workspace isolation mode. 'inherit' uses the parent's directory directly; 'branch' copies project files to a clean isolated directory; 'share' adds a git worktree.",
                    },
                },
                "required": ["name", "prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_message",
            "description": "Send a message to an active subagent (e.g. to reply or give further instructions).",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_id": {
                        "type": "string",
                        "description": "The target subagent conversation ID (returned by invoke_subagent).",
                    },
                    "message": {
                        "type": "string",
                        "description": "Text message content to send.",
                    },
                },
                "required": ["recipient_id", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_subagents",
            "description": "List or terminate active background subagents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "kill", "kill_all"],
                        "description": "Action to perform.",
                    },
                    "conversation_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of subagent conversation IDs to terminate (required for 'kill').",
                    },
                },
                "required": ["action"],
            },
        },
    },
]


def get_tools_schema() -> list[dict[str, Any]]:
    from ui.observe_mode import observe_enabled

    if observe_enabled():
        return TOOL_SCHEMAS
    return [
        schema
        for schema in TOOL_SCHEMAS
        if schema.get("function", {}).get("name") != "take_screenshot"
    ]


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
        "take_screenshot": "Screen",
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
    if tool_name == "search_symbol":
        return _quote_activity(str(args.get("query", "")))
    if tool_name == "get_codebase_map":
        return "entire workspace"
    if tool_name == "read_webpage":
        return _display_path(str(args.get("url", "")))
    if tool_name == "inspect_image":
        return _display_path(str(args.get("filepath", "")))
    if tool_name == "deep_search":
        return _quote_activity(str(args.get("query", "")))
    if tool_name == "check_syntax":
        return _display_path(str(args.get("filepath", "")))
    if tool_name == "git_status":
        return "working tree status"
    if tool_name == "git_diff":
        return "unstaged changes"
    if tool_name == "update_memory":
        return f"{args.get('category', 'fact')}: {args.get('key', '')}"
    if tool_name == "write_artifact":
        return _display_path(str(args.get("filename", "")))
    if tool_name == "web_search":
        return _quote_activity(str(args.get("query", "")))
    if tool_name == "take_screenshot":
        purpose = str(args.get("purpose", "")).strip()
        if purpose:
            return _truncate_activity(_quote_activity(purpose))
        path = str(args.get("path", "")).strip()
        return _display_path(path) if path else "desktop"
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
            msg = (
                f"Successfully wrote {len(content)} characters to {path} "
                f"(backup: {backup_path.name})"
            )
        else:
            msg = f"Successfully wrote {len(content)} characters to {path}"

        if path.suffix == ".py":
            syntax_res = check_syntax(str(path))
            if "Syntax Error" in syntax_res:
                return (
                    f"⚠️ WARNING: File written successfully, but a SYNTAX ERROR was detected!\n"
                    f"{syntax_res}\n"
                    f"Please edit this file using `apply_patch` or `write_file` to fix the syntax error."
                )
        return msg
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


def search_semantic(query: str) -> str:
    from code_search import CodeSearchIndex
    try:
        index = CodeSearchIndex(Path.cwd())
        num = index.build()
        results = index.search(query, limit=5)
        if not results:
            return "No matching code blocks found in semantic search."

        lines = [f"Semantic Search Results (indexed {num} chunks):", ""]
        for r in results:
            lines.append(f"--- File: {r['file']}:L{r['start_line']} (score: {r['score']:.4f}) ---")
            lines.append(r['text'])
            lines.append("-" * 40)
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: failed to search semantic index — {exc}"


def find_dependencies_tool(symbol: str) -> str:
    from dependency_finder import find_symbol_references
    try:
        results = find_symbol_references(Path.cwd(), symbol)
        if not results:
            return f"No references to symbol '{symbol}' found in the codebase."

        lines = [f"References to symbol '{symbol}':", ""]
        for r in results:
            lines.append(f"File: {r['file']}")
            for m in r['matches']:
                lines.append(f"  L{m['line_no']}: {m['line']}")
            lines.append("")
        return "\n".join(lines).strip()
    except Exception as exc:
        return f"Error scanning dependencies: {exc}"


def search_symbol(query: str) -> str:
    from workspace_indexer import WorkspaceIndexer
    try:
        indexer = WorkspaceIndexer(Path.cwd())
        results = indexer.search_symbol(query)
        if not results:
            return f"No symbols matching '{query}' found."
        
        lines = []
        for r in results:
            args_str = f"({', '.join(r['args'])})" if r['args'] else ""
            doc_note = f"\n  Docstring: {r['docstring']}" if r['docstring'] else ""
            lines.append(
                f"- {r['name']}{args_str} [{r['kind']}] defined in {r['file']}:L{r['start_line']}-L{r['end_line']}{doc_note}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"Error: failed to search symbol — {exc}"


def get_codebase_map() -> str:
    from workspace_indexer import WorkspaceIndexer
    try:
        indexer = WorkspaceIndexer(Path.cwd())
        return indexer.get_codebase_map()
    except Exception as exc:
        return f"Error: failed to generate codebase map — {exc}"


def read_webpage_tool(url: str) -> str:
    from web_research import read_webpage
    return read_webpage(url)


def inspect_image_tool(filepath: str) -> str:
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path
    if not path.is_file():
        return f"Error: image file not found — {filepath}"
    return f"Screenshot saved: {path}"


def deep_search_tool(query: str) -> str:
    from web_research import deep_search
    return deep_search(query)


def check_syntax(filepath: str) -> str:
    """Validate python file syntax without running it."""
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path
    if not path.is_file():
        return f"Error: file not found — {path}"
        
    if path.suffix.lower() == ".py":
        try:
            import ast
            content = path.read_text(encoding="utf-8", errors="ignore")
            ast.parse(content, filename=str(path))
            return "Syntax check passed: No python syntax errors found."
        except SyntaxError as exc:
            return f"Syntax Error in {path.name} at line {exc.lineno}, col {exc.offset}:\n{exc.text.strip() if exc.text else ''}\n-> {exc.msg}"
        except Exception as exc:
            return f"Error parsing file: {exc}"
    return "Syntax check: Supported only for Python (.py) files currently."


def git_status() -> str:
    """Get status of files in git repository."""
    try:
        git = shutil.which("git")
        if not git:
            return "Error: git is not installed or not in PATH."
        res = subprocess.run([git, "status", "--short"], capture_output=True, text=True, cwd=str(Path.cwd()))
        return res.stdout.strip() if res.stdout.strip() else "Git status: working tree clean."
    except Exception as exc:
        return f"Error running git status: {exc}"


def git_diff() -> str:
    """Get unstaged differences of files in git repository."""
    try:
        git = shutil.which("git")
        if not git:
            return "Error: git is not installed or not in PATH."
        res = subprocess.run([git, "diff"], capture_output=True, text=True, cwd=str(Path.cwd()))
        return res.stdout.strip() if res.stdout.strip() else "Git diff: no changes."
    except Exception as exc:
        return f"Error running git diff: {exc}"


def update_memory_tool(category: str, key: str, value: str) -> str:
    from skills_manager import update_project_memory
    return update_project_memory(category, key, value)


def write_artifact_tool(filename: str, content: str, summary: str) -> str:
    """Write user-facing artifact document to .axon/artifacts/ and record to timeline."""
    try:
        from ui.session_timeline import session_timeline
        root = Path.cwd() / ".axon" / "artifacts"
        root.mkdir(parents=True, exist_ok=True)
        
        clean_name = Path(filename).name
        target = root / clean_name
        
        target.write_text(content, encoding="utf-8")
        
        rel_path = f".axon/artifacts/{clean_name}"
        session_timeline.record_artifact(clean_name, summary)
        
        print(f"\n[ARTIFACT] Created/Updated: {rel_path}")
        return f"Successfully saved artifact to {rel_path} - {summary}"
    except Exception as exc:
        return f"Error: failed to write artifact — {exc}"


def apply_patch(filepath: str, patch: str) -> str:
    path = _resolve_safe_path(filepath)
    if isinstance(path, str):
        return path

    if not path.is_file():
        return f"Error: file not found — {path}"

    if "<<<<<<< ORIGINAL" in patch:
        from code_patcher import apply_search_replace_patch
        backup_manager.set_workspace(Path.cwd())
        backup_manager.backup_if_exists(path)
        success, msg = apply_search_replace_patch(path, patch)
        if success:
            _READ_FILE_CACHE.pop(str(path.resolve()), None)
            if path.suffix == ".py":
                syntax_res = check_syntax(str(path))
                if "Syntax Error" in syntax_res:
                    return (
                        f"⚠️ WARNING: Patch applied successfully, but a SYNTAX ERROR was detected!\n"
                        f"{syntax_res}\n"
                        f"Please edit this file using `apply_patch` to fix the syntax error."
                    )
            return msg
        else:
            return f"Error: {msg}"

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
    if path.suffix == ".py":
        syntax_res = check_syntax(str(path))
        if "Syntax Error" in syntax_res:
            return (
                f"⚠️ WARNING: Patch applied successfully, but a SYNTAX ERROR was detected!\n"
                f"{syntax_res}\n"
                f"Please edit this file using `apply_patch` to fix the syntax error."
            )
    return f"Successfully patched {path}"


def execute_shell(command: str) -> str:
    """Execute a shell command and return stdout/stderr."""
    cmd = command.strip()
    if not cmd:
        return "Error: command is required."

    if sys.platform == "win32":
        # Models often append cmd.exe '&' thinking it backgrounds the process.
        while cmd.endswith("&"):
            cmd = cmd[:-1].strip()

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
        if proc.returncode != 0:
            return (
                f"❌ ERROR: Command '{cmd}' failed with exit code {proc.returncode}.\n"
                f"--- OUTPUT ---\n{output or '(no output)'}\n"
                f"💡 SELF-HEALING LOOP: AXON detects a compiler/execution failure. "
                f"Please inspect the error logs, identify the bug, edit the source code using the `apply_patch` tool, "
                f"and rerun the build/test command to verify the fix."
            )
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
    if tool_name == "take_screenshot":
        from ui.observe_mode import take_screenshot_tool

        return take_screenshot_tool(str(args.get("path", "")))
    if tool_name == "web_search":
        return web_search(str(args.get("query", "")))
    if tool_name == "list_dir":
        return list_dir(str(args.get("path", ".")), bool(args.get("recursive", False)))
    if tool_name == "glob_files":
        return glob_files(str(args.get("pattern", "")), str(args.get("path", ".")))
    if tool_name == "search_code":
        return search_code(str(args.get("pattern", "")), str(args.get("path", ".")))
    if tool_name == "search_semantic":
        return search_semantic(str(args.get("query", "")))
    if tool_name == "find_dependencies":
        return find_dependencies_tool(str(args.get("symbol", "")))
    if tool_name == "search_symbol":
        return search_symbol(str(args.get("query", "")))
    if tool_name == "get_codebase_map":
        return get_codebase_map()
    if tool_name == "read_webpage":
        return read_webpage_tool(str(args.get("url", "")))
    if tool_name == "decompile_file":
        from axon_decompiler import decompile_file
        return decompile_file(
            str(args.get("file_path", "")),
            args.get("symbol_name")
        )
    if tool_name == "inspect_image":
        return inspect_image_tool(str(args.get("filepath", "")))
    if tool_name == "deep_search":
        return deep_search_tool(str(args.get("query", "")))
    if tool_name == "check_syntax":
        return check_syntax(str(args.get("filepath", "")))
    if tool_name == "git_status":
        return git_status()
    if tool_name == "git_diff":
        return git_diff()
    if tool_name == "update_memory":
        return update_memory_tool(
            str(args.get("category", "")),
            str(args.get("key", "")),
            str(args.get("value", "")),
        )
    if tool_name == "write_artifact":
        return write_artifact_tool(
            str(args.get("filename", "")),
            str(args.get("content", "")),
            str(args.get("summary", "")),
        )
    if tool_name == "apply_patch":
        return apply_patch(
            str(args.get("filepath", "")),
            str(args.get("patch", "")),
        )
    if tool_name == "schedule":
        # Extract optional numeric fields correctly
        dur = args.get("duration_seconds")
        try:
            duration_secs = int(dur) if dur is not None else None
        except (ValueError, TypeError):
            duration_secs = None
            
        return schedule_task_tool(
            prompt=str(args.get("prompt", "")),
            cron=args.get("cron"),
            duration_seconds=duration_secs,
            timer_condition=args.get("timer_condition"),
            cwd=args.get("cwd"),
        )
    if tool_name == "manage_task":
        return manage_task_tool(
            action=str(args.get("action", "")),
            task_id=args.get("task_id"),
            input_text=args.get("input_text"),
        )
    return f"Error: unknown tool '{tool_name}'."


def schedule_task_tool(
    prompt: str,
    cron: str | None = None,
    duration_seconds: int | None = None,
    timer_condition: str | None = None,
    cwd: str | None = None,
) -> str:
    from axon_schedule import add_task
    try:
        task = add_task(
            prompt,
            cron=cron,
            duration_seconds=duration_seconds,
            timer_condition=timer_condition,
            cwd=cwd,
        )
        if duration_seconds is not None:
            return f"Timer scheduled successfully with ID {task.id}. Delay: {duration_seconds}s. Condition: {timer_condition or 'never'}."
        elif cron is not None:
            return f"Task scheduled successfully with ID {task.id}. Cron expression: '{cron}'."
        else:
            return f"Task scheduled successfully with ID {task.id} daily at 09:00 AM."
    except Exception as exc:
        return f"Error: failed to schedule task — {exc}"


def manage_task_tool(
    action: str,
    task_id: str | None = None,
    input_text: str | None = None,
) -> str:
    from axon_serve import list_tasks, cancel_task
    from axon_schedule import list_tasks as list_scheduled, delete_task
    
    if action == "list":
        q_tasks = list_tasks()
        s_tasks = list_scheduled()
        
        lines = ["[Background Queue Tasks]"]
        if not q_tasks:
            lines.append("  (empty)")
        else:
            for t in q_tasks:
                lines.append(f"  ID: {t.id} | Status: {t.status} | Prompt: '{t.prompt[:50]}'")
                
        lines.append("\n[Scheduled Tasks & Timers]")
        if not s_tasks:
            lines.append("  (empty)")
        else:
            for t in s_tasks:
                type_str = "Cron" if t.cron else ("Timer" if t.duration_seconds is not None else "Daily")
                info = f"cron='{t.cron}'" if t.cron else (f"delay={t.duration_seconds}s" if t.duration_seconds is not None else f"time={t.hour:02d}:{t.minute:02d}")
                status = "triggered" if t.triggered else ("enabled" if t.enabled else "disabled")
                lines.append(f"  ID: {t.id} | Type: {type_str} ({info}) | Status: {status} | Prompt: '{t.prompt[:50]}'")
        return "\n".join(lines)
        
    if action == "kill":
        if not task_id:
            return "Error: task_id is required for action 'kill'."
        cancelled_queue = cancel_task(task_id)
        deleted_sched = delete_task(task_id)
        if cancelled_queue or deleted_sched:
            return f"Task/timer {task_id} successfully cancelled/removed."
        return f"Error: task or timer with ID '{task_id}' not found or cannot be cancelled."
        
    if action == "status":
        if not task_id:
            return "Error: task_id is required for action 'status'."
        q_tasks = list_tasks()
        for t in q_tasks:
            if t.id == task_id:
                return (
                    f"Background Task ID: {t.id}\n"
                    f"Status: {t.status}\n"
                    f"Created At: {t.created_at}\n"
                    f"Finished At: {t.finished_at}\n"
                    f"CWD: {t.cwd}\n"
                    f"Prompt: {t.prompt}\n"
                    f"Output:\n{t.output or '(none)'}"
                )
        s_tasks = list_scheduled()
        for t in s_tasks:
            if t.id == task_id:
                type_str = "Cron" if t.cron else ("Timer" if t.duration_seconds is not None else "Daily")
                info = f"cron='{t.cron}'" if t.cron else (f"delay={t.duration_seconds}s" if t.duration_seconds is not None else f"time={t.hour:02d}:{t.minute:02d}")
                return (
                    f"Scheduled Task/Timer ID: {t.id}\n"
                    f"Type: {type_str}\n"
                    f"Info: {info}\n"
                    f"Enabled: {t.enabled}\n"
                    f"Triggered: {t.triggered}\n"
                    f"Created At: {t.created_at}\n"
                    f"Last Run: {t.last_run or '(never)'}\n"
                    f"CWD: {t.cwd}\n"
                    f"Prompt: {t.prompt}\n"
                    f"Timer Condition: {t.timer_condition or 'none'}"
                )
        return f"Error: task or timer with ID '{task_id}' not found."
        
    if action == "send_input":
        return "Info: interactive stdin is not supported for background tasks in this environment."
        
    return f"Error: unknown action '{action}'."


def _needs_approval(tool_name: str) -> bool:
    from autopilot_mode import is_autopilot_active

    policy = load_runtime_policy()
    if is_autopilot_active() or policy.autonomy_enabled:
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

    if tool_name == "define_subagent":
        from subagent_manager import subagent_manager
        name = str(arguments.get("name", ""))
        system_prompt = str(arguments.get("system_prompt", ""))
        description = str(arguments.get("description", ""))
        if not name or not system_prompt:
            return "Error: name and system_prompt are required."
        res = subagent_manager.define_subagent(name, system_prompt, description)
        return f"Successfully defined subagent '{res}'."

    if tool_name == "invoke_subagent":
        from subagent_manager import subagent_manager
        from ui.observe_mode import _observe_llm as parent_llm
        name = str(arguments.get("name", ""))
        prompt = str(arguments.get("prompt", ""))
        workspace_mode = str(arguments.get("workspace_mode", "inherit"))
        if not name or not prompt:
            return "Error: name and prompt are required."
        conv_id = subagent_manager.invoke_subagent(
            name, prompt, workspace_mode=workspace_mode, parent_llm=parent_llm
        )
        return f"Successfully invoked subagent '{name}'. Conversation ID: {conv_id}."

    if tool_name == "send_message":
        from subagent_manager import subagent_manager
        recipient_id = str(arguments.get("recipient_id", ""))
        message = str(arguments.get("message", ""))
        if not recipient_id or not message:
            return "Error: recipient_id and message are required."
        ok = await subagent_manager.send_message(recipient_id, message)
        if ok:
            return "Message sent successfully."
        else:
            return f"Error: recipient '{recipient_id}' not found or not active."

    if tool_name == "manage_subagents":
        from subagent_manager import subagent_manager
        action = str(arguments.get("action", "")).strip().lower()
        if action == "list":
            sub_list = subagent_manager.list_subagents()
            if not sub_list:
                return "No active subagents."
            import json
            return json.dumps(sub_list, indent=2)
        elif action == "kill":
            ids = arguments.get("conversation_ids", [])
            if not ids:
                return "Error: conversation_ids is required for 'kill'."
            killed = []
            for cid in ids:
                if subagent_manager.kill_subagent(str(cid)):
                    killed.append(cid)
            return f"Successfully terminated subagents: {killed}"
        elif action == "kill_all":
            all_subs = subagent_manager.list_subagents()
            killed = []
            for sub in all_subs:
                cid = sub["conversation_id"]
                if subagent_manager.kill_subagent(cid):
                    killed.append(cid)
            return f"Successfully terminated all subagents: {killed}"
        else:
            return f"Error: unknown action '{action}'."

    if tool_name == "take_screenshot":
        from ui.observe_mode import observe_enabled

        if not observe_enabled():
            return (
                "Error: take_screenshot is disabled "
                "(observe_mode_enabled=false in runtime policy)."
            )

    detail = _approval_detail(tool_name, arguments)
    from ui.code_diff import build_approval_preview, combine_approval_message

    preview = ""
    if tool_name in {"write_file", "apply_patch"}:
        preview = build_approval_preview(tool_name, arguments)
    approval_message = combine_approval_message(detail, preview)

    if _needs_approval(tool_name) and not is_session_approved(tool_name, detail):
        if approve is None:
            return "User denied permission (no approval handler configured)"
        decision = await approve(tool_name, approval_message)
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

    from ui.session_timeline import session_timeline

    session_timeline.record_tool(tool_name, detail)

    log_tool_event(
        tool=tool_name,
        detail=detail,
        source=get_request_source(),
        outcome="ok" if not result.startswith("Error") else "error",
    )

    observe_note: str | None = None
    if tool_name in {"take_screenshot", "inspect_image"} and not result.startswith("Error"):
        from ui.observe_mode import enrich_screenshot_result, _resolve_screenshot_path
        from runtime_policy import load_runtime_policy
        from axon_telegram import send_telegram_photo

        policy = load_runtime_policy()
        if policy.telegram_bot_token and policy.telegram_chat_id:
            img_path = _resolve_screenshot_path(result)
            if img_path:
                send_telegram_photo(
                    policy.telegram_bot_token,
                    policy.telegram_chat_id,
                    str(img_path),
                    caption="📸 AXON: Screen Capture"
                )

        purpose = str(arguments.get("purpose", "")).strip()
        result = await enrich_screenshot_result(result, purpose=purpose)

    if _on_tool_result is not None:
        if tool_name in REQUIRES_APPROVAL:
            await _on_tool_result(tool_name, detail, result)
        elif tool_name in {"take_screenshot", "inspect_image"} and not result.startswith("Error"):
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
