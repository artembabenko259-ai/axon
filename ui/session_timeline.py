"""Session timeline — files, skills, tools, agents, cost (Cursor-style)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

EventKind = Literal["tool", "skill", "file", "observe", "agent", "plan", "cost", "artifact"]


@dataclass
class TimelineEvent:
    kind: EventKind
    label: str
    detail: str = ""
    agent: str = "AXON"


@dataclass
class SessionTimeline:
    events: list[TimelineEvent] = field(default_factory=list)
    skills_used: set[str] = field(default_factory=set)
    files_touched: set[str] = field(default_factory=set)
    _cost_anchor: float = 0.0

    def clear(self) -> None:
        self.events.clear()
        self.skills_used.clear()
        self.files_touched.clear()
        self._cost_anchor = 0.0

    def set_cost_anchor(self, total_cost: float) -> None:
        self._cost_anchor = total_cost

    def session_cost_delta(self, total_cost: float) -> float:
        return max(0.0, total_cost - self._cost_anchor)

    def _add(self, kind: EventKind, label: str, *, detail: str = "", agent: str = "AXON") -> None:
        self.events.append(
            TimelineEvent(kind=kind, label=label, detail=detail[:120], agent=agent)
        )
        if len(self.events) > 80:
            self.events = self.events[-80:]

    def record_tool(self, tool_name: str, detail: str = "", *, agent: str = "AXON") -> None:
        self._add("tool", tool_name, detail=detail, agent=agent)
        if tool_name in {"write_file", "apply_patch"} and detail.strip():
            self.files_touched.add(detail.strip()[:80])

    def record_skill(self, skill_name: str) -> None:
        name = skill_name.strip()
        if not name:
            return
        self.skills_used.add(name)
        self._add("skill", name)

    def record_file(self, path: str) -> None:
        cleaned = path.strip()
        if cleaned:
            self.files_touched.add(cleaned[:80])
            self._add("file", cleaned)

    def record_observe(self, path: str, summary: str = "") -> None:
        self._add("observe", path, detail=summary or "screenshot")

    def record_agent(self, agent: str, action: str) -> None:
        self._add("agent", action, agent=agent.strip() or "agent")

    def record_plan(self, goal: str) -> None:
        self._add("plan", goal[:60] or "plan")

    def record_artifact(self, name: str, detail: str = "") -> None:
        self._add("artifact", name, detail=detail)


session_timeline = SessionTimeline()
