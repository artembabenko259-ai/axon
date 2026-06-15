#!/usr/bin/env python3
"""AXON Live Docs — scan project, build docs.json, serve portal."""

from __future__ import annotations

import argparse
import ast
import json
import socket
import subprocess
import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

IGNORE_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "dist",
        "build",
        ".next",
        ".turbo",
        "coverage",
        ".axon/backups",
        ".idea",
        ".vscode",
    }
)

IGNORE_FILES = frozenset({".DS_Store", "Thumbs.db"})

FILE_ROLE_HINTS: dict[str, str] = {
    "main.py": "AXON CLI entry point — chat loop, slash commands, and tool orchestration.",
    "bridge.py": "WebSocket bridge connecting the CLI to the Zenith web dashboard.",
    "llm_client.py": "OpenRouter LLM client — agent loop, tool calls, and system prompts.",
    "skills_manager.py": "Dynamic SKILL.md loader and project memory reader.",
    "backup_manager.py": "Time Machine — backs up files before write_file overwrites them.",
    "task_manager.py": "Plan mode TODO board and execution state.",
    "config.json": "Runtime configuration (API keys, model selection).",
    "requirements.txt": "Python package dependencies for AXON.",
    "package.json": "Node.js dependencies for the Zenith web dashboard.",
}

EXTENSION_ROLES: dict[str, str] = {
    ".py": "Python source module.",
    ".ts": "TypeScript source file.",
    ".tsx": "React / TypeScript component.",
    ".js": "JavaScript source file.",
    ".jsx": "React component.",
    ".json": "Structured configuration or data file.",
    ".md": "Markdown documentation.",
    ".html": "HTML template or static page.",
    ".css": "Stylesheet.",
    ".yaml": "YAML configuration.",
    ".yml": "YAML configuration.",
    ".toml": "TOML configuration.",
    ".env": "Environment variable definitions.",
    ".sql": "SQL schema or query file.",
    ".sh": "Shell script.",
    ".bat": "Windows batch script.",
    ".ps1": "PowerShell script.",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def docs_output_dir(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".axon" / "docs"


def template_path() -> Path:
    return project_root() / "ui" / "docs_template.html"


def _format_annotation(node: ast.expr | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _format_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    parts: list[str] = []

    defaults_offset = len(args.args) - len(args.defaults)
    for index, arg in enumerate(args.args):
        name = arg.arg
        if arg.annotation is not None:
            name = f"{name}: {_format_annotation(arg.annotation)}"
        default_index = index - defaults_offset
        if default_index >= 0:
            default = args.defaults[default_index]
            name = f"{name}={ast.unparse(default)}"
        parts.append(name)

    if args.vararg:
        star = f"*{args.vararg.arg}"
        if args.vararg.annotation:
            star = f"*{args.vararg.arg}: {_format_annotation(args.vararg.annotation)}"
        parts.append(star)

    if args.kwonlyargs:
        if not args.vararg:
            parts.append("*")
        for index, arg in enumerate(args.kwonlyargs):
            name = arg.arg
            if arg.annotation is not None:
                name = f"{name}: {_format_annotation(arg.annotation)}"
            if index < len(args.kw_defaults) and args.kw_defaults[index] is not None:
                name = f"{name}={ast.unparse(args.kw_defaults[index])}"
            parts.append(name)

    if args.kwarg:
        kw = f"**{args.kwarg.arg}"
        if args.kwarg.annotation:
            kw = f"**{args.kwarg.arg}: {_format_annotation(args.kwarg.annotation)}"
        parts.append(kw)

    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    returns = ""
    if node.returns is not None:
        returns = f" -> {_format_annotation(node.returns)}"
    return f"{prefix} {node.name}({', '.join(parts)}){returns}"


def extract_python_symbols(path: Path) -> dict:
    """Parse a Python file with AST and return classes, functions, docstrings."""
    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        return {
            "module_docstring": "",
            "classes": [],
            "functions": [],
            "parse_error": str(exc),
        }

    classes: list[dict] = []
    functions: list[dict] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods: list[dict] = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(
                        {
                            "name": item.name,
                            "signature": _format_signature(item),
                            "docstring": ast.get_docstring(item) or "",
                            "async": isinstance(item, ast.AsyncFunctionDef),
                        }
                    )
            classes.append(
                {
                    "name": node.name,
                    "bases": [_format_annotation(base) for base in node.bases],
                    "docstring": ast.get_docstring(node) or "",
                    "methods": methods,
                }
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(
                {
                    "name": node.name,
                    "signature": _format_signature(node),
                    "docstring": ast.get_docstring(node) or "",
                    "async": isinstance(node, ast.AsyncFunctionDef),
                }
            )

    return {
        "module_docstring": ast.get_docstring(tree) or "",
        "classes": classes,
        "functions": functions,
        "parse_error": None,
    }


def infer_file_role(path: Path, rel: str) -> str:
    """Human-readable summary for non-Python or supplemental context."""
    name = path.name
    if name in FILE_ROLE_HINTS:
        return FILE_ROLE_HINTS[name]

    parent = path.parent.name
    if parent == "skills" and name == "tools.py":
        return "Native agent tools — read_file, write_file, shell, web_search."
    if parent == "skills" and name == "tasks.py":
        return "Plan mode tools — create_plan and complete_task."
    if parent == "ui":
        return f"UI module — {name} for the AXON terminal interface."
    if "zenith-web" in rel.replace("\\", "/"):
        return f"Zenith web dashboard — {name}."

    ext = path.suffix.lower()
    if ext in EXTENSION_ROLES:
        return EXTENSION_ROLES[ext]

    if path.is_dir():
        return f"Project directory — {name}/."

    return f"Project file — {name}."


def should_skip_dir(name: str) -> bool:
    return name in IGNORE_DIRS or name.startswith(".")


def walk_project(workspace: Path) -> tuple[list[dict], dict[str, dict]]:
    """Build file tree and per-file documentation index."""
    files_index: dict[str, dict] = {}
    tree: list[dict] = []

    def walk_dir(directory: Path, rel_base: str = "") -> list[dict]:
        nodes: list[dict] = []
        try:
            entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return nodes

        for entry in entries:
            if entry.name in IGNORE_FILES:
                continue
            rel = f"{rel_base}/{entry.name}" if rel_base else entry.name
            rel = rel.replace("\\", "/")

            if entry.is_dir():
                if should_skip_dir(entry.name):
                    continue
                children = walk_dir(entry, rel)
                if not children:
                    continue
                node = {
                    "name": entry.name,
                    "path": rel,
                    "type": "directory",
                    "children": children,
                }
                nodes.append(node)
                files_index[rel] = {
                    "path": rel,
                    "kind": "directory",
                    "summary": infer_file_role(entry, rel),
                }
                continue

            if entry.suffix.lower() in {".pyc", ".pyo", ".so", ".dll", ".exe", ".ico", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".map", ".lock"}:
                continue

            kind = "python" if entry.suffix.lower() == ".py" else "file"
            file_doc: dict = {
                "path": rel,
                "kind": kind,
                "name": entry.name,
                "extension": entry.suffix.lower(),
                "summary": infer_file_role(entry, rel),
            }

            try:
                file_doc["size_bytes"] = entry.stat().st_size
            except OSError:
                file_doc["size_bytes"] = 0

            if kind == "python":
                symbols = extract_python_symbols(entry)
                file_doc.update(symbols)
                if not file_doc.get("module_docstring") and file_doc.get("summary"):
                    file_doc["module_docstring"] = file_doc["summary"]

            files_index[rel] = file_doc
            nodes.append(
                {
                    "name": entry.name,
                    "path": rel,
                    "type": "file",
                    "kind": kind,
                }
            )

        return nodes

    tree = walk_dir(workspace)
    return tree, files_index


def build_search_index(files_index: dict[str, dict]) -> list[dict]:
    """Flatten classes and functions for global search."""
    index: list[dict] = []

    for path, doc in files_index.items():
        if doc.get("kind") == "directory":
            continue

        summary = doc.get("summary", "")
        if summary:
            index.append(
                {
                    "type": "file",
                    "name": doc.get("name", Path(path).name),
                    "file": path,
                    "signature": "",
                    "detail": summary,
                }
            )

        for fn in doc.get("functions", []):
            index.append(
                {
                    "type": "function",
                    "name": fn["name"],
                    "file": path,
                    "signature": fn.get("signature", ""),
                    "detail": fn.get("docstring", ""),
                }
            )

        for cls in doc.get("classes", []):
            index.append(
                {
                    "type": "class",
                    "name": cls["name"],
                    "file": path,
                    "signature": f"class {cls['name']}",
                    "detail": cls.get("docstring", ""),
                }
            )
            for method in cls.get("methods", []):
                index.append(
                    {
                        "type": "method",
                        "name": f"{cls['name']}.{method['name']}",
                        "file": path,
                        "signature": method.get("signature", ""),
                        "detail": method.get("docstring", ""),
                    }
                )

    return index


def generate_docs(workspace: Path | None = None) -> Path:
    """Walk project, write docs.json and index.html. Returns output directory."""
    root = workspace or Path.cwd()
    out = docs_output_dir(root)
    out.mkdir(parents=True, exist_ok=True)

    tree, files_index = walk_project(root)
    payload = {
        "project": root.name,
        "root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tree": tree,
        "files": files_index,
        "search_index": build_search_index(files_index),
        "stats": {
            "file_count": sum(1 for f in files_index.values() if f.get("kind") != "directory"),
            "python_count": sum(1 for f in files_index.values() if f.get("kind") == "python"),
            "class_count": sum(len(f.get("classes", [])) for f in files_index.values()),
            "function_count": sum(
                len(f.get("functions", []))
                + sum(len(c.get("methods", [])) for c in f.get("classes", []))
                for f in files_index.values()
            ),
        },
    }

    (out / "docs.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    template = template_path()
    if template.is_file():
        (out / "index.html").write_text(
            template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    else:
        (out / "index.html").write_text(
            "<!DOCTYPE html><html><body><h1>docs_template.html missing</h1>"
            "<p>Run from AXON project root.</p></body></html>",
            encoding="utf-8",
        )

    return out


def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def start_server_background(
    workspace: Path | None = None,
    port: int = 8000,
) -> subprocess.Popen | None:
    """Start serve_docs.py in background if port is not already in use."""
    if is_port_open(port):
        return None

    serve_script = project_root() / "scripts" / "serve_docs.py"
    proc = subprocess.Popen(
        [sys.executable, str(serve_script), "--port", str(port), "--workspace", str(workspace or Path.cwd())],
        cwd=str(workspace or Path.cwd()),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
    )
    return proc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AXON Live Docs")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-serve", action="store_true", help="Only generate, do not start server")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    out = generate_docs(workspace)
    print(f"Generated docs in {out}")

    if not args.no_serve:
        start_server_background(workspace, port=args.port)
        url = f"http://localhost:{args.port}"
        if not args.no_browser:
            webbrowser.open(url)
        print(f"[OK] Docs available at {url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
