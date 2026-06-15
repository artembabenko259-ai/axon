from __future__ import annotations

from pathlib import Path
from typing import Any

from skills.base import BaseSkill

MAX_FILE_SIZE = 64 * 1024


class FileReadSkill(BaseSkill):
    """Reads the contents of a file by path."""

    def get_name(self) -> str:
        return "file_read"

    def get_description(self) -> str:
        return (
            "Reads and returns the contents of a file at the given path. "
            f"Files larger than {MAX_FILE_SIZE // 1024} KB are truncated."
        )

    def get_parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read.",
                },
            },
            "required": ["path"],
        }

    def execute(self, args: dict[str, Any]) -> str:
        path_str = args.get("path", "").strip()
        if not path_str:
            return "Error: 'path' argument is required."

        try:
            path = Path(path_str).resolve()
        except (OSError, ValueError) as exc:
            return f"Error: invalid path — {exc}"

        if ".." in Path(path_str).parts:
            return "Error: path traversal ('..') is not allowed."

        if not path.is_file():
            return f"Error: file not found — {path}"

        try:
            size = path.stat().st_size
            if size > MAX_FILE_SIZE:
                content = path.read_text(encoding="utf-8", errors="replace")[
                    :MAX_FILE_SIZE
                ]
                return (
                    f"{content}\n\n"
                    f"[Truncated: file is {size} bytes, "
                    f"showing first {MAX_FILE_SIZE} bytes]"
                )
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Error: could not read file — {exc}"
