"""Simple scheduled AXON tasks (run via Task Scheduler or `axon schedule run`)."""

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
    hour: int
    minute: int
    prompt: str
    cwd: str
    enabled: bool = True
    last_run: str = ""


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
                hour=int(item.get("hour", 9)),
                minute=int(item.get("minute", 0)),
                prompt=str(item.get("prompt", "")),
                cwd=str(item.get("cwd", "")),
                enabled=bool(item.get("enabled", True)),
                last_run=str(item.get("last_run", "")),
            )
        )
    return out


def _save(tasks: list[ScheduledTask]) -> None:
    SCHEDULE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULE_PATH.write_text(
        json.dumps([asdict(t) for t in tasks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def add_task(
    prompt: str,
    *,
    hour: int,
    minute: int,
    cwd: str | None = None,
) -> ScheduledTask:
    tasks = _load()
    task = ScheduledTask(
        id=uuid.uuid4().hex[:8],
        hour=hour,
        minute=minute,
        prompt=prompt.strip(),
        cwd=str(Path(cwd or Path.cwd()).resolve()),
    )
    tasks.append(task)
    _save(tasks)
    return task


def list_tasks() -> list[ScheduledTask]:
    return _load()


def run_due(*, force_all: bool = False) -> int:
    now = datetime.now()
    tasks = _load()
    changed = False
    exe = install_root() / "axon.exe"
    for task in tasks:
        if not task.enabled and not force_all:
            continue
        if not force_all and (now.hour != task.hour or now.minute != task.minute):
            continue
        if exe.is_file():
            cmd = [str(exe), "-p", task.prompt, "--cwd", task.cwd]
        else:
            cmd = [
                sys.executable,
                str(install_root() / "cli.py"),
                "-p",
                task.prompt,
                "--cwd",
                task.cwd,
            ]
        print(f"[schedule] {task.id} @ {task.hour:02d}:{task.minute:02d}")
        subprocess.call(cmd)
        task.last_run = datetime.now(timezone.utc).isoformat()
        changed = True
    if changed:
        _save(tasks)
    return 0
