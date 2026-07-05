"""Background task queue — run AXON prompts while you work elsewhere."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from axon_runtime import install_root, user_data_dir

QUEUE_PATH = user_data_dir() / "task_queue.json"
POLL_SECONDS = 2.0

# Global tracking of active running Popen instances.
RUNNING_PROCESSES: dict[str, subprocess.Popen] = {}


@dataclass
class QueuedTask:
    id: str
    prompt: str
    cwd: str
    status: str = "pending"  # pending, running, done, cancelled
    created_at: str = ""
    finished_at: str = ""
    output: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def _load_queue() -> list[QueuedTask]:
    if not QUEUE_PATH.is_file():
        return []
    try:
        raw = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    tasks: list[QueuedTask] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        tasks.append(
            QueuedTask(
                id=str(item.get("id", "")),
                prompt=str(item.get("prompt", "")),
                cwd=str(item.get("cwd", "")),
                status=str(item.get("status", "pending")),
                created_at=str(item.get("created_at", "")),
                finished_at=str(item.get("finished_at", "")),
                output=str(item.get("output", "")),
            )
        )
    return tasks


def _save_queue(tasks: list[QueuedTask]) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(
        json.dumps([asdict(t) for t in tasks], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def enqueue(prompt: str, *, cwd: str | None = None) -> QueuedTask:
    tasks = _load_queue()
    task = QueuedTask(
        id=uuid.uuid4().hex[:10],
        prompt=prompt.strip(),
        cwd=str(Path(cwd or Path.cwd()).resolve()),
    )
    tasks.append(task)
    _save_queue(tasks)
    return task


def list_tasks() -> list[QueuedTask]:
    return _load_queue()


def cancel_task(task_id: str) -> bool:
    """Kill process if running, or mark as cancelled if pending."""
    # 1. Kill active process if running
    process_killed = False
    p = RUNNING_PROCESSES.get(task_id)
    if p:
        try:
            p.terminate()
            p.wait(timeout=2.0)
            process_killed = True
        except Exception:
            try:
                p.kill()
                process_killed = True
            except Exception:
                pass
        if task_id in RUNNING_PROCESSES:
            del RUNNING_PROCESSES[task_id]

    # 2. Update status in file
    tasks = _load_queue()
    updated = False
    for task in tasks:
        if task.id == task_id:
            if task.status in {"pending", "running"}:
                task.status = "cancelled"
                task.finished_at = datetime.now(timezone.utc).isoformat()
                task.output += "\n[cancelled by user]"
                updated = True
                break
    if updated:
        _save_queue(tasks)
        return True
    return process_killed


def _axon_cmd() -> list[str]:
    bundled = install_root() / "axon.exe"
    if bundled.is_file():
        return [str(bundled)]
    return [sys.executable, str(install_root() / "cli.py")]


def _run_task(task: QueuedTask) -> str:
    cmd = _axon_cmd() + ["-p", task.prompt, "--cwd", task.cwd]
    try:
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=task.cwd,
        )
        RUNNING_PROCESSES[task.id] = p
        stdout, stderr = p.communicate(timeout=3600)
        out = (stdout or "") + (stderr or "")
        return out.strip() or f"(exit {p.returncode})"
    except subprocess.TimeoutExpired:
        proc = RUNNING_PROCESSES.get(task.id)
        if proc:
            proc.kill()
            stdout, stderr = proc.communicate()
            out = (stdout or "") + (stderr or "")
        return "AXON: task timed out after 3600s"
    except OSError as exc:
        return f"AXON: failed to run task — {exc}"
    finally:
        if task.id in RUNNING_PROCESSES:
            del RUNNING_PROCESSES[task.id]


def process_next() -> QueuedTask | None:
    tasks = _load_queue()
    for task in tasks:
        if task.status != "pending":
            continue
        task.status = "running"
        _save_queue(tasks)
        task.output = _run_task(task)
        # If cancelled in the meantime, don't overwrite done
        current_tasks = _load_queue()
        for ct in current_tasks:
            if ct.id == task.id:
                if ct.status == "running":
                    ct.status = "done"
                    ct.output = task.output
                    ct.finished_at = datetime.now(timezone.utc).isoformat()
                break
        _save_queue(current_tasks)
        
        try:
            from axon_notifications import notify_agent_complete
            notify_agent_complete()
        except Exception:
            pass
        return task
    return None


def run_serve(*, once: bool = False, tray: bool = False) -> int:
    print("AXON serve — background queue (Ctrl+C to stop)")
    print(f"Queue file: {QUEUE_PATH}")

    if tray:
        import threading
        from axon_tray import run_tray

        threading.Thread(
            target=run_tray,
            kwargs={"panel_url": "http://127.0.0.1:3000"},
            daemon=True,
        ).start()
        print("Tray icon active (Open Zenith / Quit from menu).")

    from axon_schedule import run_due as run_scheduled_due

    try:
        while True:
            # 1. Run due scheduled tasks & timers
            try:
                run_scheduled_due()
            except Exception as exc:
                print(f"[schedule error] {exc}")

            # 2. Process next background queue task
            task = process_next()
            if task:
                print(f"[done] {task.id}: {task.prompt[:60]}…")
                
            if once and not any(t.status == "pending" for t in _load_queue()):
                return 0
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
