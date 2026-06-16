"""Cursor-style task board state for AXON TUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

TaskBoardStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class TaskBoardItem:
    key: str
    label: str
    status: TaskBoardStatus = "pending"
    detail: str = ""


@dataclass
class TaskBoardState:
    title: str = ""
    items: list[TaskBoardItem] = field(default_factory=list)

    def clear(self) -> None:
        self.title = ""
        self.items.clear()

    def set_items(self, title: str, items: list[TaskBoardItem]) -> None:
        self.title = title
        self.items = list(items)

    @property
    def visible(self) -> bool:
        return bool(self.title or self.items)
