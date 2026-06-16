#!/usr/bin/env python3
"""AXON CLI — unified command-line entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axon",
        description="AXON — agentic command-line AI assistant",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("repl", help="Interactive REPL (default)")
    sub.add_parser("tui", help="Fullscreen terminal UI (lighter than REPL)")

    mt_p = sub.add_parser("multitask", help="Run orchestrator headless")
    mt_p.add_argument("goal", help="Goal to decompose and run")
    mt_p.add_argument(
        "--agents",
        metavar="NAMES",
        help="Comma-separated agent names (optional)",
    )
    mt_p.add_argument("--json", action="store_true", help="JSON output")
    mt_p.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve dangerous tools",
    )

    sub.add_parser("tray", help="System tray icon (Windows)")

    export_p = sub.add_parser("export", help="Export a saved session to Markdown")
    export_p.add_argument("session_id", nargs="?", help="Session id (latest if omitted)")
    export_p.add_argument("-o", "--output", metavar="PATH", help="Output .md path")

    serve_p = sub.add_parser("serve", help="Process background task queue")
    serve_p.add_argument(
        "--once",
        action="store_true",
        help="Process pending tasks once and exit",
    )
    serve_p.add_argument(
        "--tray",
        action="store_true",
        help="Show system tray icon while serving (Windows)",
    )

    queue_p = sub.add_parser("queue", help="Background task queue")
    queue_sub = queue_p.add_subparsers(dest="queue_cmd", required=True)
    queue_add = queue_sub.add_parser("add", help="Enqueue a headless prompt")
    queue_add.add_argument("task", help="Task for axon -p")
    queue_add.add_argument("--cwd", metavar="DIR", help="Working directory")
    queue_sub.add_parser("list", help="List queued tasks")

    watch_p = sub.add_parser("watch", help="Watch folder and run AXON on changes")
    watch_p.add_argument("path", nargs="?", default=".", help="Directory to watch")
    watch_p.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Poll interval in seconds",
    )
    watch_p.add_argument("-p", "--prompt", metavar="TEXT", help="Custom prompt")

    sched_p = sub.add_parser("schedule", help="Scheduled headless tasks")
    sched_sub = sched_p.add_subparsers(dest="schedule_cmd", required=True)
    sched_add = sched_sub.add_parser("add", help="Add daily task")
    sched_add.add_argument("task", help="Prompt to run")
    sched_add.add_argument("--hour", type=int, default=9)
    sched_add.add_argument("--minute", type=int, default=0)
    sched_add.add_argument("--cwd", metavar="DIR")
    sched_sub.add_parser("list", help="List scheduled tasks")
    sched_sub.add_parser("run", help="Run tasks due now (for Task Scheduler)")

    doctor = sub.add_parser("doctor", help="Check local AXON environment")
    doctor.add_argument("--json", action="store_true", help="JSON output")
    doctor.add_argument(
        "--check-updates",
        action="store_true",
        help="Check runaxon.xyz for a newer release",
    )

    sub.add_parser("version", help="Print AXON version")

    update = sub.add_parser("update", help="Check for AXON updates")
    update.add_argument("--json", action="store_true", help="JSON output")

    web = sub.add_parser("web", help="Start Zenith web dashboard (dev server)")
    web.add_argument("--port", type=int, default=3000)
    web.add_argument(
        "--open",
        action="store_true",
        help="Open http://localhost:<port> in the default browser",
    )

    login = sub.add_parser("login", help="Sign in via runaxon.xyz (email)")
    login.add_argument(
        "--force",
        action="store_true",
        help="Sign out and start a new browser login flow",
    )
    login.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the browser automatically",
    )

    sub.add_parser("logout", help="Sign out of AXON account on this machine")

    # Headless flags (Phase 4) — attached to root for `axon -p "..."`
    parser.add_argument(
        "-p",
        "--prompt",
        metavar="TEXT",
        help="Run a single prompt and exit (headless)",
    )
    parser.add_argument("--cwd", metavar="DIR", help="Working directory")
    parser.add_argument("--model", metavar="NAME", help="Override model")
    parser.add_argument("--json", action="store_true", help="JSON output (headless)")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Auto-approve dangerous tools in headless mode",
    )

    return parser


def _run_doctor(*, json_output: bool, check_updates: bool = False) -> int:
    from axon_doctor import run_doctor

    return run_doctor(json_output=json_output, check_updates=check_updates)


def _run_version() -> int:
    from ui.branding import VERSION

    print(f"AXON {VERSION}")
    return 0


def _run_update(*, json_output: bool) -> int:
    import json as json_mod

    from version_check import check_for_update

    available, message, release = check_for_update()
    if json_output:
        print(
            json_mod.dumps(
                {
                    "update_available": available,
                    "message": message,
                    "current": __import__("ui.branding", fromlist=["VERSION"]).VERSION,
                    "latest": release.version if release else None,
                    "download_url": release.download_url if release else "",
                    "winget_id": release.winget_id if release else "",
                },
                indent=2,
            )
        )
    else:
        print(message)
    return 0 if not available else 2


def _run_web(port: int, *, open_browser: bool) -> int:
    from zenith_server import (
        DEFAULT_ZENITH_PORT,
        has_bundled_zenith,
        panel_url,
        run_zenith_dev,
        run_zenith_foreground,
    )

    if open_browser:
        import threading
        import time
        import webbrowser

        def _open() -> None:
            time.sleep(2.5)
            webbrowser.open(panel_url(port))

        threading.Thread(target=_open, daemon=True).start()

    if has_bundled_zenith():
        return run_zenith_foreground(port)

    web_dir = ROOT / "zenith-web"
    if (web_dir / "package.json").is_file():
        return run_zenith_dev(port)

    print("AXON: Zenith panel not found.", file=sys.stderr)
    print("AXON: Reinstall AXON or run from the development repository.", file=sys.stderr)
    return 1


def _run_logout() -> int:
    from axon_auth import logout

    logout()
    print("Signed out.")
    return 0


def _run_tui() -> int:
    from ui.axon_tui import run_tui

    try:
        run_tui()
    except KeyboardInterrupt:
        pass
    return 0


def _run_export(session_id: str | None, output: str | None) -> int:
    from session_export import export_messages_markdown, export_session_markdown
    from session_store import list_sessions, load_session

    if session_id:
        try:
            path = export_session_markdown(
                session_id,
                output=Path(output) if output else None,
            )
        except FileNotFoundError as exc:
            print(f"AXON: {exc}", file=sys.stderr)
            return 1
        print(path)
        return 0

    sessions = list_sessions()
    if not sessions:
        print("AXON: no saved sessions — run /save in the REPL first.", file=sys.stderr)
        return 1
    path = export_session_markdown(
        sessions[0].id,
        output=Path(output) if output else None,
    )
    print(path)
    return 0


def _run_serve(*, once: bool, tray: bool = False) -> int:
    from axon_serve import run_serve

    return run_serve(once=once, tray=tray)


def _run_multitask(
    goal: str,
    *,
    agents: str | None,
    json_output: bool,
    auto_approve: bool,
) -> int:
    from axon_multitask_cli import run_multitask_headless

    agent_list = None
    if agents:
        from agent_manager import sanitize_agent_name

        agent_list = [sanitize_agent_name(n) for n in agents.split(",") if n.strip()]
    return run_multitask_headless(
        goal,
        agents=agent_list,
        json_output=json_output,
        auto_approve=auto_approve,
    )


def _run_tray() -> int:
    from axon_tray import run_tray_blocking

    try:
        run_tray_blocking()
    except KeyboardInterrupt:
        pass
    return 0


def _run_queue(command: str, *, prompt: str = "", cwd: str | None = None) -> int:
    from axon_serve import enqueue, list_tasks

    if command == "add":
        if not prompt.strip():
            print("AXON: queue add requires a prompt.", file=sys.stderr)
            return 1
        task = enqueue(prompt, cwd=cwd)
        print(f"Queued {task.id}: {task.prompt[:60]}")
        return 0
    if command == "list":
        tasks = list_tasks()
        if not tasks:
            print("(empty)")
            return 0
        for t in tasks:
            print(f"{t.id}  [{t.status}]  {t.prompt[:70]}")
        return 0
    return 1


def _run_watch(path: str, *, interval: float, prompt: str | None) -> int:
    from axon_watch import run_watch

    return run_watch(
        Path(path),
        interval=interval,
        prompt=prompt or "",
    )


def _run_schedule(command: str, **kwargs) -> int:
    from axon_schedule import add_task, list_tasks, run_due

    if command == "add":
        task = add_task(
            kwargs.get("prompt", ""),
            hour=int(kwargs.get("hour", 9)),
            minute=int(kwargs.get("minute", 0)),
            cwd=kwargs.get("cwd"),
        )
        print(f"Scheduled {task.id} daily at {task.hour:02d}:{task.minute:02d}")
        return 0
    if command == "list":
        tasks = list_tasks()
        if not tasks:
            print("(empty)")
            return 0
        for t in tasks:
            flag = "on" if t.enabled else "off"
            print(f"{t.id}  [{flag}]  {t.hour:02d}:{t.minute:02d}  {t.prompt[:50]}")
        return 0
    if command == "run":
        return run_due()
    return 1


def _run_login(*, force: bool, open_browser: bool) -> int:
    from axon_auth import load_session, logout, run_login_flow, session_summary

    if force:
        logout()
    else:
        existing = load_session()
        if existing:
            print(session_summary())
            print("Use: axon login --force   or   axon logout")
            return 0

    try:
        session = run_login_flow(open_browser=open_browser)
        print(f"Signed in as {session.email}")
        return 0
    except RuntimeError as exc:
        print(f"AXON: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Pipe-to-axon only when no explicit subcommand (avoid blocking on closed stdin).
    if args.prompt is None and args.command is None and not sys.stdin.isatty():
        piped = sys.stdin.read().strip()
        if piped:
            args.prompt = piped

    if args.cwd:
        try:
            import os

            os.chdir(args.cwd)
        except OSError as exc:
            print(f"AXON: invalid --cwd — {exc}", file=sys.stderr)
            return 1

    command = args.command or "repl"

    if args.prompt and args.command is None:
        from ui.headless import run_headless

        return run_headless(
            args.prompt,
            model=args.model,
            json_output=args.json,
            auto_approve=args.yes,
        )

    if command == "doctor":
        return _run_doctor(
            json_output=args.json,
            check_updates=getattr(args, "check_updates", False),
        )

    if command == "version":
        return _run_version()

    if command == "update":
        return _run_update(json_output=args.json)

    if command == "web":
        return _run_web(args.port, open_browser=getattr(args, "open", False))

    if command == "login":
        return _run_login(
            force=getattr(args, "force", False),
            open_browser=not getattr(args, "no_open", False),
        )

    if command == "logout":
        return _run_logout()

    if command == "tui":
        return _run_tui()

    if command == "multitask":
        return _run_multitask(
            getattr(args, "goal", ""),
            agents=getattr(args, "agents", None),
            json_output=getattr(args, "json", False),
            auto_approve=getattr(args, "yes", False),
        )

    if command == "tray":
        return _run_tray()

    if command == "export":
        return _run_export(
            getattr(args, "session_id", None),
            getattr(args, "output", None),
        )

    if command == "serve":
        return _run_serve(
            once=getattr(args, "once", False),
            tray=getattr(args, "tray", False),
        )

    if command == "queue":
        return _run_queue(
            args.queue_cmd,
            prompt=getattr(args, "task", ""),
            cwd=getattr(args, "cwd", None),
        )

    if command == "watch":
        return _run_watch(
            getattr(args, "path", "."),
            interval=getattr(args, "interval", 5.0),
            prompt=getattr(args, "prompt", None),
        )

    if command == "schedule":
        return _run_schedule(
            args.schedule_cmd,
            prompt=getattr(args, "task", ""),
            hour=getattr(args, "hour", 9),
            minute=getattr(args, "minute", 0),
            cwd=getattr(args, "cwd", None),
        )

    from ui.repl import start_axon

    try:
        asyncio.run(start_axon())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
