from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from rich.panel import Panel

TaskStatus = Literal["pending", "in-progress", "done"]

STATUS_ICONS: dict[TaskStatus, str] = {
    "done": "[green][✓][/]",
    "in-progress": "[yellow][↻][/]",
    "pending": "[dim][ ][/]",
}


@dataclass
class PlanTask:
    id: int
    name: str
    status: TaskStatus = "pending"


@dataclass
class TaskManager:
    """In-memory plan / TODO board for AXON Plan Mode."""

    tasks: list[PlanTask] = field(default_factory=list)
    goal: str = ""
    plan_mode: bool = False
    execution_mode: bool = False

    def has_plan(self) -> bool:
        return bool(self.tasks)

    def clear(self) -> None:
        self.tasks.clear()
        self.goal = ""
        self.plan_mode = False
        self.execution_mode = False

    def create_plan(self, tasks: list[str], *, goal: str = "") -> list[PlanTask]:
        cleaned = [task.strip() for task in tasks if task and str(task).strip()]
        self.tasks = [
            PlanTask(id=index, name=name, status="pending")
            for index, name in enumerate(cleaned, start=1)
        ]
        if goal:
            self.goal = goal.strip()
        if self.tasks:
            self.tasks[0].status = "in-progress"
        self.plan_mode = False
        return list(self.tasks)

    def update_task_status(self, task_id: int, status: str) -> PlanTask | None:
        normalized = status.strip().lower().replace("_", "-")
        if normalized not in STATUS_ICONS:
            normalized = "pending"

        task = self._find(task_id)
        if task is None:
            return None

        task.status = normalized  # type: ignore[assignment]

        if normalized == "in-progress":
            for other in self.tasks:
                if other.id != task_id and other.status == "in-progress":
                    other.status = "pending"

        if normalized == "done":
            next_pending = next(
                (item for item in self.tasks if item.status == "pending"),
                None,
            )
            if next_pending is not None:
                next_pending.status = "in-progress"

        return task

    def complete_task(self, task_id: int) -> PlanTask | None:
        return self.update_task_status(task_id, "done")

    def get_plan_markdown(self) -> str:
        if not self.tasks:
            return "[dim]No active plan. Use /plan <description> to create one.[/]"

        lines: list[str] = []
        if self.goal:
            lines.append(f"[bold]Goal:[/] {self.goal}\n")

        for task in self.tasks:
            icon = STATUS_ICONS.get(task.status, STATUS_ICONS["pending"])
            if task.status == "in-progress":
                lines.append(f"{icon} [yellow]{task.id}. {task.name}[/]")
            elif task.status == "done":
                lines.append(f"{icon} [dim strike]{task.id}. {task.name}[/]")
            else:
                lines.append(f"{icon} {task.id}. {task.name}")

        done = sum(1 for task in self.tasks if task.status == "done")
        lines.append(f"\n[dim]{done}/{len(self.tasks)} completed[/]")
        return "\n".join(lines)

    def build_plan_panel(self) -> Panel:
        return Panel(
            self.get_plan_markdown(),
            title="📋 AXON Plan",
            border_style="cyan",
            padding=(0, 1),
        )

    def all_done(self) -> bool:
        return bool(self.tasks) and all(task.status == "done" for task in self.tasks)

    def _find(self, task_id: int) -> PlanTask | None:
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None


# Shared session instance used by CLI and task tools.
task_manager = TaskManager()
