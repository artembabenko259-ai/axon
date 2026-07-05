"""Scheduled AXON tasks and one-shot timers (run via task serve loop or `axon schedule run`)."""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from axon_runtime import install_root, user_data_dir

SCHEDULE_PATH = user_data_dir() / "scheduled_tasks.json"


@dataclass
class ScheduledTask:
    id: str
    prompt: str
    cwd: str
    hour: int = 9
    minute: int = 0
    cron: str | None = None
    duration_seconds: int | None = None
    timer_condition: str | None = None
    created_at: str = ""
    enabled: bool = True
    last_run: str = ""
    triggered: bool = False

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def _load() -> list[ScheduledTask]:
    if not SCHEDULE_PATH.is_file():
        return []
    try:
        raw = json.loads(SCHEDULE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out: list[ScheduledTask] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        out.append(
            ScheduledTask(
                id=str(item.get("id", "")),
                prompt=str(item.get("prompt", "")),
                cwd=str(item.get("cwd", "")),
                hour=int(item.get("hour", 9)),
                minute=int(item.get("minute", 0)),
                cron=item.get("cron"),
                duration_seconds=item.get("duration_seconds"),
                timer_condition=item.get("timer_condition"),
                created_at=str(item.get("created_at", "")),
                enabled=bool(item.get("enabled", True)),
                last_run=str(item.get("last_run", "")),
                triggered=bool(item.get("triggered", False)),
            )
        )
    return out


def _save(tasks: list[ScheduledTask]) -> None:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(
        json.dumps([asdict(t) for t in tasks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def match_cron(expression: str, dt: datetime) -> bool:
    """Matches standard 5-field cron: minute hour day month day_of_week."""
    parts = expression.strip().split()
    if len(parts) != 5:
        return False
    
    def match_field(field_val: int, pattern: str) -> bool:
        if pattern == "*":
            return True
        for part in pattern.split(","):
            if "/" in part:
                subpattern, step_str = part.split("/")
                step = int(step_str)
                if subpattern == "*":
                    if field_val % step == 0:
                        return True
                else:
                    try:
                        start = int(subpattern)
                        if field_val >= start and (field_val - start) % step == 0:
                            return True
                    except ValueError:
                        pass
            elif "-" in part:
                try:
                    start_str, end_str = part.split("-")
                    if int(start_str) <= field_val <= int(end_str):
                        return True
                except ValueError:
                    pass
            else:
                try:
                    if int(part) == field_val:
                        return True
                except ValueError:
                    pass
        return False

    cron_weekday = dt.weekday() + 1
    if cron_weekday == 7:
        cron_weekday = 0  # Sunday

    return (
        match_field(dt.minute, parts[0])
        and match_field(dt.hour, parts[1])
        and match_field(dt.day, parts[2])
        and match_field(dt.month, parts[3])
        and match_field(dt.weekday() if parts[4] in ["*", "?"] else cron_weekday, parts[4])
    )


def add_task(
    prompt: str,
    *,
    hour: int = 9,
    minute: int = 0,
    cron: str | None = None,
    duration_seconds: int | None = None,
    timer_condition: str | None = None,
    cwd: str | None = None,
) -> ScheduledTask:
    tasks = _load()
    task = ScheduledTask(
        id=uuid.uuid4().hex[:8],
        prompt=prompt.strip(),
        cwd=str(Path(cwd or Path.cwd()).resolve()),
        hour=hour,
        minute=minute,
        cron=cron,
        duration_seconds=duration_seconds,
        timer_condition=timer_condition,
    )
    tasks.append(task)
    _save(tasks)
    return task


def list_tasks() -> list[ScheduledTask]:
    return _load()


def delete_task(task_id: str) -> bool:
    tasks = _load()
    filtered = [t for t in tasks if t.id != task_id]
    if len(filtered) < len(tasks):
        _save(filtered)
        return True
    return False


def run_due(*, force_all: bool = False) -> int:
    now = datetime.now()
    now_utc = datetime.now(timezone.utc)
    tasks = _load()
    changed = False
    exe = install_root() / "axon.exe"
    
    for task in tasks:
        if not task.enabled or task.triggered:
            continue
            
        due = False
        
        # 1. One-shot timer
        if task.duration_seconds is not None:
            try:
                created = datetime.fromisoformat(task.created_at)
                elapsed = (now_utc - created).total_seconds()
                if elapsed >= task.duration_seconds:
                    due = True
                    task.triggered = True
            except Exception:
                pass
                
        # 2. Cron expression
        elif task.cron is not None:
            if match_cron(task.cron, now):
                due = True
                
        # 3. Simple hour/minute daily task
        else:
            if now.hour == task.hour and now.minute == task.minute:
                due = True
                
        if due or force_all:
            # Check timer condition before running
            if task.timer_condition and task.timer_condition != "never":
                # Check if target task or condition is met. For simplicity, we check if
                # the target task ID in queue has finished, or if 'any' is set and queue is busy.
                # If timer_condition is a task ID, and that task is already done, we cancel running.
                if task.timer_condition == "any":
                    pass # Run anyway, or custom logic
                else:
                    from axon_serve import list_tasks as list_queue_tasks
                    matched = next((qt for qt in list_queue_tasks() if qt.id == task.timer_condition), None)
                    if matched and matched.status in {"done", "cancelled"}:
                        print(f"[schedule] Timer cancelled early due to condition: {task.timer_condition}")
                        task.triggered = True
                        changed = True
                        continue

            if exe.is_file():
                cmd = [str(exe), "-p", task.prompt, "--cwd", task.cwd, "--yes"]
            else:
                cmd = [
                    sys.executable,
                    str(install_root() / "cli.py"),
                    "-p",
                    task.prompt,
                    "--cwd",
                    task.cwd,
                    "--yes",
                ]
            print(f"[schedule] Running: {task.id} -> '{task.prompt}'")
            subprocess.call(cmd)
            task.last_run = datetime.now(timezone.utc).isoformat()
            changed = True
            
    if changed:
        _save(tasks)
    return 0
