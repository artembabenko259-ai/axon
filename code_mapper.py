"""AST-based codebase skeleton map generator for AXON context injection."""

from __future__ import annotations

import re
from pathlib import Path

# Common directories to ignore
IGNORE_DIRS = {
    ".git", ".axon", "node_modules", "venv", "env", "__pycache__",
    "build", "dist", ".next", "out", "target", "obj", "bin"
}

# Supported file extensions
SUPPORTED_EXTS = {
    ".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".cpp", ".hpp",
    ".h", ".c", ".rs", ".java", ".cs"
}


def scan_file_symbols(file_path: Path) -> list[str]:
    """Scans a file using fast regex parser to extract signatures (classes, functions, structs)."""
    symbols: list[str] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return symbols

    lines = content.splitlines()
    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith(("//", "#", "/*", "*")):
            continue

        # Python class/def
        if file_path.suffix == ".py":
            match_class = re.match(r"^\s*class\s+([a-zA-Z0-9_]+)", line)
            if match_class:
                symbols.append(f"  class {match_class.group(1)}")
            match_def = re.match(r"^\s*def\s+([a-zA-Z0-9_]+)\((.*?)\)", line)
            if match_def:
                symbols.append(f"  def {match_def.group(1)}()")

        # Go func/struct/interface
        elif file_path.suffix == ".go":
            match_func = re.match(r"^func\s+(?:\(.*?\)\s+)?([a-zA-Z0-9_]+)\(", line_strip)
            if match_func:
                symbols.append(f"  func {match_func.group(1)}()")
            match_struct = re.match(r"^type\s+([a-zA-Z0-9_]+)\s+(struct|interface)", line_strip)
            if match_struct:
                symbols.append(f"  type {match_struct.group(1)} {match_struct.group(2)}")

        # TypeScript / JavaScript classes and functions
        elif file_path.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            match_class = re.match(r"^(?:export\s+)?class\s+([a-zA-Z0-9_]+)", line_strip)
            if match_class:
                symbols.append(f"  class {match_class.group(1)}")
            match_func = re.search(r"\bfunction\s+([a-zA-Z0-9_]+)\(", line_strip)
            if match_func:
                symbols.append(f"  function {match_func.group(1)}()")
            # Async arrow functions or exports
            match_const_func = re.match(r"^(?:export\s+)?const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\(.*?\)\s*=>", line_strip)
            if match_const_func:
                symbols.append(f"  const {match_const_func.group(1)}()")

        # Rust struct/enum/fn/trait
        elif file_path.suffix == ".rs":
            match_fn = re.match(r"^(?:pub\s+)?(?:async\s+)?fn\s+([a-zA-Z0-9_]+)", line_strip)
            if match_fn:
                symbols.append(f"  fn {match_fn.group(1)}()")
            match_struct = re.match(r"^(?:pub\s+)?(?:struct|enum|trait)\s+([a-zA-Z0-9_]+)", line_strip)
            if match_struct:
                symbols.append(f"  {match_struct.group(0)}")

        # C++ / C / Java / C# methods
        elif file_path.suffix in {".cpp", ".hpp", ".h", ".c", ".java", ".cs"}:
            # Basic method match
            match_method = re.match(r"^(?:public|private|protected|static|virtual|inline)\s+[a-zA-Z0-9_<>]+\s+([a-zA-Z0-9_]+)\(", line_strip)
            if match_method:
                symbols.append(f"  method {match_method.group(1)}()")
            match_class = re.match(r"^(?:class|struct)\s+([a-zA-Z0-9_]+)", line_strip)
            if match_class:
                symbols.append(f"  class/struct {match_class.group(1)}")

    return symbols


def generate_code_map(workspace_path: str | Path) -> str:
    """Recursively walks the workspace and compiles a summary map of all source code symbols."""
    root = Path(workspace_path)
    lines: list[str] = ["=== AXON Workspace Symbol Map ==="]

    try:
        for p in sorted(root.rglob("*")):
            # Check if any parent folder is ignored
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.is_file() and p.suffix in SUPPORTED_EXTS:
                rel_path = p.relative_to(root).as_posix()
                symbols = scan_file_symbols(p)
                if symbols:
                    lines.append(f"\nFile: {rel_path}")
                    lines.extend(symbols[:20])  # Cap at 20 symbols per file to save space
                    if len(symbols) > 20:
                        lines.append("  ... (truncated)")
    except Exception as exc:
        return f"Error scanning workspace symbols: {exc}"

    return "\n".join(lines)
