"""Workspace Indexer for AXON — fast AST parsing of class and function structures."""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

IGNORE_DIRS = {
    ".git",
    ".axon",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "out",
}


@dataclass
class SymbolInfo:
    name: str
    kind: str  # "class" | "function" | "method"
    start_line: int
    end_line: int
    docstring: str = ""
    args: list[str] = field(default_factory=list)


@dataclass
class FileIndex:
    path: str  # relative to workspace root
    size: int
    symbols: list[SymbolInfo] = field(default_factory=list)


class WorkspaceIndexer:
    def __init__(self, workspace_path: Path):
        self.workspace_path = workspace_path.resolve()
        self.index_dir = self.workspace_path / ".axon"
        self.index_file = self.index_dir / "workspace_index.json"

    def should_ignore(self, path: Path) -> bool:
        for part in path.parts:
            part_lower = part.lower()
            if part in IGNORE_DIRS or "venv" in part_lower or "site-packages" in part_lower:
                return True
        return False

    def parse_python_file(self, file_path: Path) -> list[SymbolInfo]:
        symbols: list[SymbolInfo] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))
        except Exception:
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node) or ""
                end_line = getattr(node, "end_lineno", node.lineno)
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind="class",
                        start_line=node.lineno,
                        end_line=end_line,
                        docstring=doc.strip(),
                    )
                )
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                doc = ast.get_docstring(node) or ""
                end_line = getattr(node, "end_lineno", node.lineno)
                args = [arg.arg for arg in node.args.args]
                
                # Determine if it's a method
                kind = "function"
                # If parent is a ClassDef in hierarchy (but ast.walk is flat, so we do a quick check)
                # For simplicity, we flag as function/method. We can check if it's defined inside a ClassDef
                # by traversing child nodes or just labelling it based on parentage.
                symbols.append(
                    SymbolInfo(
                        name=node.name,
                        kind=kind,
                        start_line=node.lineno,
                        end_line=end_line,
                        docstring=doc.strip(),
                        args=args,
                    )
                )
        return symbols

    def parse_js_ts_file(self, file_path: Path) -> list[SymbolInfo]:
        """Simple regex-based parser for JS/TS classes and functions."""
        symbols: list[SymbolInfo] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []

        lines = content.splitlines()
        
        # Regex patterns
        class_pat = re.compile(r"class\s+(?P<name>\w+)")
        func_pat = re.compile(r"(?:function\s+(?P<name1>\w+)|const\s+(?P<name2>\w+)\s*=\s*(?:\([^)]*\)|[^=]+)=>\s*\{)")

        for idx, line in enumerate(lines):
            line_num = idx + 1
            class_match = class_pat.search(line)
            if class_match:
                symbols.append(
                    SymbolInfo(
                        name=class_match.group("name"),
                        kind="class",
                        start_line=line_num,
                        end_line=line_num,
                    )
                )
                continue

            func_match = func_pat.search(line)
            if func_match:
                name = func_match.group("name1") or func_match.group("name2")
                if name:
                    symbols.append(
                        SymbolInfo(
                            name=name,
                            kind="function",
                            start_line=line_num,
                            end_line=line_num,
                        )
                    )
        return symbols

    def scan_and_index(self) -> dict[str, dict]:
        index_data: dict[str, dict] = {}
        
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [
                d for d in dirs
                if d not in IGNORE_DIRS and "venv" not in d.lower() and "site-packages" not in d.lower()
            ]
            
            for file in files:
                file_path = Path(root) / file
                if self.should_ignore(file_path):
                    continue

                suffix = file_path.suffix.lower()
                symbols: list[SymbolInfo] = []

                if suffix == ".py":
                    symbols = self.parse_python_file(file_path)
                elif suffix in {".js", ".jsx", ".ts", ".tsx"}:
                    symbols = self.parse_js_ts_file(file_path)
                else:
                    # Skip non-code files for symbols but track existence if needed
                    continue

                try:
                    rel_path = str(file_path.relative_to(self.workspace_path)).replace("\\", "/")
                    size = file_path.stat().st_size
                    index_data[rel_path] = asdict(
                        FileIndex(path=rel_path, size=size, symbols=symbols)
                    )
                except Exception:
                    pass

        # Save to disk
        self.index_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.index_file.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
        except Exception as exc:
            print(f"[indexer error] Failed to save index: {exc}")

        return index_data

    def load_index(self) -> dict[str, dict]:
        if not self.index_file.is_file():
            return self.scan_and_index()
        try:
            return json.loads(self.index_file.read_text(encoding="utf-8"))
        except Exception:
            return self.scan_and_index()

    def search_symbol(self, query: str) -> list[dict]:
        index = self.load_index()
        results = []
        query_lower = query.lower()

        for file_path, file_data in index.items():
            for sym in file_data.get("symbols", []):
                if query_lower in sym["name"].lower():
                    results.append({
                        "file": file_path,
                        "name": sym["name"],
                        "kind": sym["kind"],
                        "start_line": sym["start_line"],
                        "end_line": sym["end_line"],
                        "args": sym.get("args", []),
                        "docstring": sym.get("docstring", "")
                    })
        return results

    def get_codebase_map(self) -> str:
        index = self.load_index()
        lines = []
        for file_path, file_data in sorted(index.items()):
            symbols = file_data.get("symbols", [])
            if not symbols:
                continue
            lines.append(f"File: {file_path}")
            for sym in symbols:
                prefix = "  [Class]" if sym["kind"] == "class" else "  [Func]"
                args_str = f"({', '.join(sym.get('args', []))})" if sym.get("args") else ""
                lines.append(f"{prefix} {sym['name']}{args_str} [L{sym['start_line']}]")
        return "\n".join(lines) if lines else "No indexable code files found in this workspace."
