from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from task_manager import task_manager

PlanRenderCallback = Callable[[], Awaitable[None]]
MultitaskRunner = Callable[[str], Awaitable[str]]

_on_plan_update: PlanRenderCallback | None = None
_multitask_runner: MultitaskRunner | None = None

TASK_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": (
                "Create a step-by-step plan with 3-5 logical tasks. "
                "Use in Plan Mode before executing any work."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered list of task descriptions",
                    },
                    "goal": {
                        "type": "string",
                        "description": "Optional short summary of the overall goal",
                    },
                },
                "required": ["tasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": (
                "Mark a plan task as completed. Call this after finishing each step "
                "during plan execution."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "integer",
                        "description": "Numeric id of the task to complete",
                    },
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_status",
            "description": (
                "Update a task status to pending, in-progress, or done. "
                "Use in-progress for the task currently being worked on."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in-progress", "done"],
                    },
                },
                "required": ["task_id", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_multitask",
            "description": (
                "Decompose a complex goal into parallel subtasks, run them with "
                "sub-agents, and return a unified synthesis. Use when the user wants "
                "multiple independent workstreams (review + tests + docs) without "
                "a strict sequential plan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "Full goal to decompose and execute in parallel",
                    },
                },
                "required": ["goal"],
            },
        },
    },
]

TASK_TOOL_NAMES = frozenset(
    {"create_plan", "complete_task", "update_task_status", "run_multitask"}
)


def get_task_tool_schemas() -> list[dict[str, Any]]:
    return TASK_TOOL_SCHEMAS


def set_plan_render_callback(callback: PlanRenderCallback | None) -> None:
    global _on_plan_update
    _on_plan_update = callback


def set_multitask_runner(callback: MultitaskRunner | None) -> None:
    global _multitask_runner
    _multitask_runner = callback


async def _render_plan() -> None:
    if _on_plan_update is not None:
        await _on_plan_update()


async def execute_task_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "create_plan":
        raw_tasks = arguments.get("tasks", [])
        if not isinstance(raw_tasks, list):
            raw_tasks = [str(raw_tasks)]
        tasks = [str(item) for item in raw_tasks if str(item).strip()]
        if not tasks:
            return "Error: create_plan requires at least one task."
        goal = str(arguments.get("goal", "")).strip()
        created = task_manager.create_plan(tasks, goal=goal or task_manager.goal)
        await _render_plan()
        names = ", ".join(f"{task.id}:{task.name}" for task in created)
        return f"Plan created with {len(created)} task(s): {names}"

    if tool_name == "complete_task":
        try:
            task_id = int(arguments.get("task_id", 0))
        except (TypeError, ValueError):
            return "Error: task_id must be an integer."
        task = task_manager.complete_task(task_id)
        if task is None:
            return f"Error: task id {task_id} not found."
        await _render_plan()
        if task_manager.all_done():
            return f"Task {task_id} completed. All plan tasks are done."
        return f"Task {task_id} marked done: {task.name}"

    if tool_name == "update_task_status":
        try:
            task_id = int(arguments.get("task_id", 0))
        except (TypeError, ValueError):
            return "Error: task_id must be an integer."
        status = str(arguments.get("status", "pending"))
        task = task_manager.update_task_status(task_id, status)
        if task is None:
            return f"Error: task id {task_id} not found."
        await _render_plan()
        return f"Task {task_id} set to {task.status}: {task.name}"

    if tool_name == "run_multitask":
        goal = str(arguments.get("goal", "")).strip()
        if not goal:
            return "Error: run_multitask requires a goal string."
        if _multitask_runner is None:
            return "Error: multitask runner is not configured in this session."
        try:
            return await _multitask_runner(goal)
        except Exception as exc:
            return f"Error: multitask failed — {exc}"

    return f"Error: unknown task tool '{tool_name}'."


def is_task_tool(tool_name: str) -> bool:
    return tool_name in TASK_TOOL_NAMES
