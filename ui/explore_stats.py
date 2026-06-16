"""Cursor-style turn summary: Explored N files, M searches."""

from __future__ import annotations

from dataclasses import dataclass, field

_FILE_TOOLS = frozenset({"read_file"})
_SEARCH_TOOLS = frozenset({"search_code", "glob_files", "web_search", "list_dir"})


@dataclass
class ExploreStats:
    files: int = 0
    searches: int = 0
    _seen_files: set[str] = field(default_factory=set, repr=False)

    def record(self, tool_name: str, detail: str = "") -> None:
        if tool_name in _FILE_TOOLS:
            key = detail.strip() or f"#{self.files}"
            if key not in self._seen_files:
                self._seen_files.add(key)
                self.files += 1
        elif tool_name in _SEARCH_TOOLS:
            self.searches += 1

    def summary(self) -> str | None:
        if self.files == 0 and self.searches == 0:
            return None
        parts: list[str] = []
        if self.files:
            noun = "file" if self.files == 1 else "files"
            parts.append(f"Explored {self.files} {noun}")
        if self.searches:
            noun = "search" if self.searches == 1 else "searches"
            parts.append(f"{self.searches} {noun}")
        return ", ".join(parts)


_turn: ExploreStats = ExploreStats()


def reset_turn_explore_stats() -> None:
    global _turn
    _turn = ExploreStats()


def record_explore_tool(tool_name: str, detail: str = "") -> None:
    _turn.record(tool_name, detail)


def get_turn_explore_summary() -> str | None:
    return _turn.summary()
