"""Detect when natural language should route to plan / multitask."""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal["chat", "plan", "multitask"]

_PLAN_PATTERNS = (
    r"\bplan\b",
    r"\bплан\b",
    r"разбей на (шаги|задачи|этапы)",
    r"составь план",
    r"break (this )?into steps",
    r"step[- ]by[- ]step",
    r"розбий на (кроки|задачі)",
    r"склади план",
)

_MULTITASK_PATTERNS = (
    r"\bmultitask\b",
    r"мультизадач",
    r"параллельно",
    r"паралельно",
    r"несколько агент",
    r"кілька агент",
    r"in parallel",
    r"split.*agents",
    r"orchestrat",
    r"одновременно",
)


def detect_intent(text: str) -> Intent:
    stripped = text.strip()
    if not stripped or stripped.startswith("/"):
        if stripped.lower().startswith("/plan"):
            return "plan"
        if stripped.lower().startswith("/multitask"):
            return "multitask"
        return "chat"

    lower = stripped.lower()
    if len(lower) < 12:
        return "chat"

    for pattern in _MULTITASK_PATTERNS:
        if re.search(pattern, lower):
            return "multitask"

    for pattern in _PLAN_PATTERNS:
        if re.search(pattern, lower):
            return "plan"

    # Complex multi-part goals without explicit command
    if lower.count(",") >= 2 and any(
        word in lower
        for word in ("and", "та", "и", "also", "потім", "затем", "then")
    ):
        return "multitask"

    return "chat"
