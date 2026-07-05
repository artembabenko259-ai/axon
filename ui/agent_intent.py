"""Detect when natural language should route to plan / multitask."""

from __future__ import annotations

import re
from typing import Literal

Intent = Literal["chat", "plan", "multitask", "execute"]

_PLAN_PATTERNS = (
    r"\bплан\b",
    r"разбей на (шаги|задачи|этапы)",
    r"составь план",
    r"склади план",
    r"break (this )?into steps",
    r"step[- ]by[- ]step",
    r"розбий на (кроки|задачі)",
    r"roadmap",
    r"outline (the )?work",
    r"\b(create|make|build|draft)\s+(a\s+)?plan\b",
    r"\bplan\s+(this|the|for|out)\b",
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
    r"паралельн",
    r"sub-?agents?",
    r"разбей на части",
)

_EXECUTE_PATTERNS = (
    r"выполни план",
    r"запусти план",
    r"запусти выполнение",
    r"execute (the )?plan",
    r"start (the )?plan",
    r"run (the )?plan",
)


def _has_parallel_intent(lower: str) -> bool:
    return any(re.search(p, lower) for p in _MULTITASK_PATTERNS)


def _has_plan_intent(lower: str) -> bool:
    return any(re.search(p, lower) for p in _PLAN_PATTERNS)


def _has_execute_intent(lower: str) -> bool:
    return any(re.search(p, lower) for p in _EXECUTE_PATTERNS)


def detect_intent(text: str, *, has_active_plan: bool = False) -> Intent:
    stripped = text.strip()
    if not stripped:
        return "chat"

    if stripped.startswith("/"):
        low = stripped.lower()
        if low.startswith("/plan"):
            return "plan"
        if low.startswith("/multitask"):
            return "multitask"
        if low.startswith("/execute"):
            return "execute"
        return "chat"

    lower = stripped.lower()

    if has_active_plan and _has_execute_intent(lower):
        return "execute"

    parallel = _has_parallel_intent(lower)
    plan = _has_plan_intent(lower)

    if parallel and not plan:
        return "multitask"
    if plan and not parallel:
        return "plan"
    if parallel and plan:
        return "multitask" if _parallel_wins(lower) else "plan"

    if lower.count(",") >= 1 and any(
        word in lower
        for word in ("and", "та", "и", "also", "потім", "затем", "then", "а также")
    ):
        return "multitask"

    return "chat"


def _parallel_wins(lower: str) -> bool:
    parallel_words = ("parallel", "параллель", "паралель", "одновременно", "agents", "агент")
    return any(word in lower for word in parallel_words)
