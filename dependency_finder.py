"""Code dependency finder and symbol reference scanner for AXON refactoring context."""

from __future__ import annotations

import re
from pathlib import Path

# Directories to ignore
IGNORE_DIRS = {
    ".git", ".axon", "node_modules", "venv", "env", "__pycache__",
    "build", "dist", ".next", "out", "target", "obj", "bin"
}

# Supported file extensions
SUPPORTED_EXTS = {
    ".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".cpp", ".hpp",
    ".h", ".c", ".rs", ".java", ".cs"
}


def find_symbol_references(workspace_path: str | Path, symbol_name: str) -> list[dict[str, any]]:
    """
    Scans the workspace for any references (imports, calls, instantiations)
    to the given symbol name, using word-boundary regex matching.
    """
    root = Path(workspace_path)
    references: list[dict[str, any]] = []
    
    if not symbol_name.strip():
        return references

    # Regex matches word boundaries around symbol_name
    pattern = re.compile(rf"\b{re.escape(symbol_name)}\b")

    try:
        for p in root.rglob("*"):
            if any(part in IGNORE_DIRS for part in p.parts):
                continue
            if p.is_file() and p.suffix in SUPPORTED_EXTS:
                # Read content and search
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                if pattern.search(content):
                    rel_path = p.relative_to(root).as_posix()
                    lines = content.splitlines()
                    file_matches = []
                    
                    for line_no, line in enumerate(lines, start=1):
                        if pattern.search(line):
                            # Skip definition lines to keep focus on usages
                            if re.search(r"(def|class|func|struct|fn|type)\s+" + re.escape(symbol_name), line):
                                continue
                            file_matches.append({
                                "line_no": line_no,
                                "line": line.strip()[:140]
                            })
                    
                    if file_matches:
                        references.append({
                            "file": rel_path,
                            "matches": file_matches
                        })
    except Exception as exc:
        print(f"[dependency finder error] {exc}")

    return references
