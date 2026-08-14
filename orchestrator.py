"""AXON Orchestrator — decompose goals and run parallel sub-agent tasks."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from agent_manager import list_agents, sanitize_agent_name
from llm_client import LLMManager

MAX_SUBTASKS = 5
MAX_PARALLEL = 3
DEFAULT_AGENT = "axon"

SubTaskStatus = Literal["pending", "running", "done", "failed"]

_STATUS_ICONS: dict[SubTaskStatus, str] = {
    "pending": "[dim][ ][/]",
    "running": "[yellow][>][/]",
    "done": "[green][✓][/]",
    "failed": "[red][x][/]",
}

_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


@dataclass
class SubTask:
    id: int
    title: str
    agent: str
    task: str
    status: SubTaskStatus = "pending"
    result: str = ""
    error: str | None = None


@dataclass
class OrchestratorResult:
    goal: str
    subtasks: list[SubTask]
    synthesis: str = ""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


ProgressCallback = Callable[[str], Awaitable[None] | None]
MultitaskEventCallback = Callable[
    [str, str, list[SubTask], str], Awaitable[None] | None
]


@dataclass
class Orchestrator:
    llm: LLMManager
    workspace: Path
    allow_parallel: bool = False
    max_parallel: int = MAX_PARALLEL

    _last_run: OrchestratorResult | None = field(default=None, init=False, repr=False)

    def parse_command(self, stripped: str) -> tuple[str, list[str]]:
        """Parse `/multitask [--agents a,b] <goal>`."""
        text = stripped.strip()
        if not text.lower().startswith("/multitask"):
            return "", []

        rest = text[len("/multitask") :].strip()
        agents: list[str] = []
        if rest.startswith("--agents"):
            match = re.match(r"--agents\s+(\S+)(?:\s+(.*))?$", rest, re.DOTALL)
            if match:
                agents = [
                    sanitize_agent_name(name)
                    for name in match.group(1).split(",")
                    if name.strip()
                ]
                rest = (match.group(2) or "").strip()
            else:
                rest = ""
        return rest, agents

    async def run(
        self,
        goal: str,
        *,
        preferred_agents: list[str] | None = None,
        on_progress: ProgressCallback | None = None,
        on_multitask_event: MultitaskEventCallback | None = None,
    ) -> OrchestratorResult:
        goal = goal.strip()
        if not goal:
            result = OrchestratorResult(
                goal="",
                subtasks=[],
                error="AXON: /multitask requires a goal description.",
            )
            self._last_run = result
            return result

        await self._emit_multitask(
            on_multitask_event, "decompose_start", goal, [], ""
        )
        await self._emit(on_progress, "[bold]Step 1/3[/] Decomposing goal into subtasks...")
        subtasks = await self._decompose(goal, preferred_agents=preferred_agents or [])
        if not subtasks:
            result = OrchestratorResult(
                goal=goal,
                subtasks=[],
                error="AXON: Could not create subtasks for this goal.",
            )
            self._last_run = result
            return result

        await self._emit_multitask(
            on_multitask_event, "decompose_done", goal, subtasks, ""
        )
        await self._emit(on_progress, self._render_board(subtasks, goal))
        await self._emit(
            on_progress,
            "[bold]Step 2/3[/] Running subtasks "
            + ("in parallel (max 3)..." if self.allow_parallel else "sequentially..."),
        )

        if self.allow_parallel:
            await self._run_parallel(
                subtasks,
                goal=goal,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )
        else:
            await self._run_sequential(
                subtasks,
                goal=goal,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )

        await self._emit(on_progress, self._render_board(subtasks, goal))
        await self._emit(on_progress, "[bold]Step 3/3[/] Synthesizing results...")

        synthesis = await self._synthesize(goal, subtasks)
        await self._emit_multitask(
            on_multitask_event, "synthesis_done", goal, subtasks, synthesis
        )
        result = OrchestratorResult(goal=goal, subtasks=subtasks, synthesis=synthesis)
        self._last_run = result
        return result

    def last_run(self) -> OrchestratorResult | None:
        return self._last_run

    async def _decompose(
        self,
        goal: str,
        *,
        preferred_agents: list[str],
    ) -> list[SubTask]:
        available = list_agents(self.workspace)
        hints = preferred_agents or available
        agent_hint = ", ".join(hints) if hints else "(none — use axon for all)"

        system = (
            "You are AXON Orchestrator. Split the user's goal into 2-5 independent "
            "subtasks that can run in parallel without blocking each other. "
            "Return ONLY valid JSON, no markdown outside the JSON object:\n"
            '{"subtasks":[{"title":"short label","agent":"axon","task":"detailed prompt"}]}\n'
            'Use agent "axon" for general coding/research. '
            "Use a specialist name only when it clearly fits and appears in Available agents."
        )
        user = (
            f"Goal:\n{goal}\n\n"
            f"Available agents: {agent_hint}\n"
            f"Default agent: {DEFAULT_AGENT}"
        )

        parsed = await self._decompose_with_llm(system, user)
        if parsed:
            return self._normalize_subtasks(parsed, available, preferred_agents)

        return [
            SubTask(
                id=1,
                title="Full goal",
                agent=DEFAULT_AGENT,
                task=goal,
            )
        ]

    async def _decompose_with_llm(self, system: str, user: str) -> list[dict[str, str]]:
        result = await self.llm.complete_text_async(system=system, user=user)
        if not result.ok or not result.content:
            return []
        payload = _extract_json(result.content)
        if not isinstance(payload, dict):
            return []
        raw_tasks = payload.get("subtasks")
        if not isinstance(raw_tasks, list):
            return []
        items: list[dict[str, str]] = []
        for entry in raw_tasks[:MAX_SUBTASKS]:
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title", "")).strip()
            task = str(entry.get("task", "")).strip()
            agent = sanitize_agent_name(str(entry.get("agent", DEFAULT_AGENT)))
            if title and task:
                items.append({"title": title, "agent": agent, "task": task})
        return items

    def _normalize_subtasks(
        self,
        items: list[dict[str, str]],
        available: list[str],
        preferred: list[str],
    ) -> list[SubTask]:
        available_set = set(available)
        preferred_cycle = preferred or available
        subtasks: list[SubTask] = []

        for index, item in enumerate(items[:MAX_SUBTASKS], start=1):
            agent = item["agent"]
            if agent != DEFAULT_AGENT and agent not in available_set:
                if preferred_cycle:
                    agent = preferred_cycle[(index - 1) % len(preferred_cycle)]
                else:
                    agent = DEFAULT_AGENT
            subtasks.append(
                SubTask(
                    id=index,
                    title=item["title"],
                    agent=agent,
                    task=item["task"],
                )
            )
        return subtasks

    async def _run_sequential(
        self,
        subtasks: list[SubTask],
        *,
        goal: str,
        on_progress: ProgressCallback | None,
        on_multitask_event: MultitaskEventCallback | None,
    ) -> None:
        for subtask in subtasks:
            await self._run_one(
                subtask,
                goal=goal,
                subtasks=subtasks,
                on_progress=on_progress,
                on_multitask_event=on_multitask_event,
            )

    async def _run_parallel(
        self,
        subtasks: list[SubTask],
        *,
        goal: str,
        on_progress: ProgressCallback | None,
        on_multitask_event: MultitaskEventCallback | None,
    ) -> None:
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def _wrapped(task: SubTask) -> None:
            async with semaphore:
                await self._run_one(
                    task,
                    goal=goal,
                    subtasks=subtasks,
                    on_progress=on_progress,
                    on_multitask_event=on_multitask_event,
                )

        await asyncio.gather(*[_wrapped(task) for task in subtasks])

    async def _run_one(
        self,
        subtask: SubTask,
        *,
        goal: str,
        subtasks: list[SubTask],
        on_progress: ProgressCallback | None,
        on_multitask_event: MultitaskEventCallback | None,
    ) -> None:
        subtask.status = "running"
        await self._emit_multitask(
            on_multitask_event, "subtask_status", goal, subtasks, ""
        )
        await self._emit(
            on_progress,
            f"[cyan]▶ Task {subtask.id}[/] [{subtask.agent}] {subtask.title}",
        )

        worker = self.llm.spawn_worker()
        try:
            if subtask.agent == DEFAULT_AGENT:
                result = await worker.send_message_async(subtask.task)
            else:
                result = await worker.send_delegated_async(
                    subtask.agent,
                    subtask.task,
                )
        except Exception as exc:
            subtask.status = "failed"
            subtask.error = str(exc)
            await self._emit_multitask(
                on_multitask_event, "subtask_status", goal, subtasks, ""
            )
            await self._emit(
                on_progress,
                f"[red]✗ Task {subtask.id} failed — {exc}[/]",
            )
            return

        if result.ok and result.content:
            subtask.status = "done"
            subtask.result = result.content.strip()
            preview = subtask.result.replace("\n", " ")
            if len(preview) > 120:
                preview = preview[:117] + "..."
            await self._emit_multitask(
                on_multitask_event, "subtask_status", goal, subtasks, ""
            )
            await self._emit(
                on_progress,
                f"[green]✓ Task {subtask.id} done[/] [dim]{preview}[/]",
            )
        else:
            subtask.status = "failed"
            subtask.error = result.display_text
            await self._emit_multitask(
                on_multitask_event, "subtask_status", goal, subtasks, ""
            )
            await self._emit(
                on_progress,
                f"[red]✗ Task {subtask.id}[/] {result.display_text}",
            )

    async def _synthesize(self, goal: str, subtasks: list[SubTask]) -> str:
        lines: list[str] = []
        for task in subtasks:
            header = f"### Task {task.id}: {task.title} ({task.agent}) — {task.status}"
            if task.status == "done":
                body = task.result
            else:
                body = task.error or "No output."
            lines.append(f"{header}\n{body}")

        system = (
            "You are AXON Orchestrator. Merge subtask outputs into one clear summary "
            "for the user. Use markdown headings and bullet lists. "
            "Note failures honestly. Do not invent work that was not done."
        )
        user = f"User goal:\n{goal}\n\nSubtask outputs:\n\n" + "\n\n".join(lines)

        result = await self.llm.complete_text_async(system=system, user=user, temperature=0.3)
        if result.ok and result.content:
            return result.content.strip()

        fallback_parts = [f"## Goal\n{goal}\n"]
        for task in subtasks:
            icon = "OK" if task.status == "done" else "FAILED"
            fallback_parts.append(
                f"### [{icon}] {task.title} ({task.agent})\n"
                f"{task.result or task.error or '(empty)'}\n"
            )
        if result.error:
            fallback_parts.append(f"\n_Synthesis error: {result.error}_")
        return "\n".join(fallback_parts)

    def _render_board(self, subtasks: list[SubTask], goal: str) -> str:
        lines = [f"[bold]Goal:[/] {goal}", ""]
        for task in subtasks:
            icon = _STATUS_ICONS.get(task.status, _STATUS_ICONS["pending"])
            agent = f"[magenta]{task.agent}[/]"
            lines.append(f"{icon} {task.id}. {task.title} — {agent}")
        done = sum(1 for task in subtasks if task.status == "done")
        lines.append(f"\n[dim]{done}/{len(subtasks)} completed[/]")
        return "\n".join(lines)

    async def _emit(self, callback: ProgressCallback | None, message: str) -> None:
        if not callback:
            return
        maybe = callback(message)
        if asyncio.iscoroutine(maybe):
            await maybe

    async def _emit_multitask(
        self,
        callback: MultitaskEventCallback | None,
        phase: str,
        goal: str,
        subtasks: list[SubTask],
        synthesis: str,
    ) -> None:
        if not callback:
            return
        maybe = callback(phase, goal, subtasks, synthesis)
        if asyncio.iscoroutine(maybe):
            await maybe


def _extract_json(text: str) -> Any:
    text = text.strip()
    for block in _JSON_BLOCK_RE.findall(text):
        try:
            return json.loads(block.strip())
        except json.JSONDecodeError:
            continue
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    return None
