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

    repl_p = sub.add_parser("repl", help="Rich REPL with full slash commands and WebSocket bridge")
    repl_p.add_argument("--headless", action="store_true", help="Run headlessly, serving WebSocket bridge")
    sub.add_parser("tui", help="Fullscreen terminal UI (default)")

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

    autopilot_p = sub.add_parser("autopilot", help="Autopilot full autonomy (admin terminal)")
    autopilot_sub = autopilot_p.add_subparsers(dest="autopilot_cmd")
    autopilot_sub.add_parser("status", help="Show Autopilot state")
    autopilot_sub.add_parser("on", help="Enable Autopilot (elevated process required)")
    autopilot_sub.add_parser("off", help="Disable Autopilot")

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
    sched_add.add_argument("--cron", help="Cron pattern, e.g. '*/5 * * * *'")
    sched_add.add_argument("--timer", type=int, help="One-shot delay in seconds")
    sched_add.add_argument("--timer-cond", help="Timer condition: 'never', 'any', or a task ID")
    sched_add.add_argument("--cwd", metavar="DIR")
    sched_sub.add_parser("list", help="List scheduled tasks")
    sched_sub.add_parser("run", help="Run tasks due now (for Task Scheduler)")

    sub.add_parser("shard", help="Bubble Tea Go-based TUI client")
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


def _run_autopilot(action: str) -> int:
    from autopilot_mode import handle_autopilot_arg

    code, msg = handle_autopilot_arg(action)
    print(msg)
    return code


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
            cron=kwargs.get("cron"),
            duration_seconds=kwargs.get("timer"),
            timer_condition=kwargs.get("timer_cond"),
            cwd=kwargs.get("cwd"),
        )
        if task.duration_seconds is not None:
            print(f"Scheduled {task.id}: Timer ({task.duration_seconds}s delay)")
        elif task.cron is not None:
            print(f"Scheduled {task.id}: Cron ({task.cron})")
        else:
            print(f"Scheduled {task.id} daily at {task.hour:02d}:{task.minute:02d}")
        return 0
    if command == "list":
        tasks = list_tasks()
        if not tasks:
            print("(empty)")
            return 0
        for t in tasks:
            flag = "on" if t.enabled else "off"
            if t.duration_seconds is not None:
                info = f"Timer ({t.duration_seconds}s)"
            elif t.cron is not None:
                info = f"Cron ({t.cron})"
            else:
                info = f"Daily {t.hour:02d}:{t.minute:02d}"
            print(f"{t.id}  [{flag}]  {info:<18}  {t.prompt[:50]}")
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


def _run_shard() -> int:
    import os
    import sys
    import time
    import socket
    import subprocess
    import shutil
    from pathlib import Path

    executable_name = "axon-shard.exe" if os.name == "nt" else "axon-shard"
    
    # 1. Search in the installation/root directory
    local_path = Path(__file__).parent / executable_name
    if local_path.exists():
        exe_path = str(local_path)
    else:
        # 2. Try looking in dist/
        dist_path = Path(__file__).parent / "dist" / "shard" / executable_name
        if dist_path.exists():
            exe_path = str(dist_path)
        else:
            # 3. Check system PATH
            found_path = shutil.which(executable_name)
            if found_path:
                exe_path = found_path
            else:
                print("AXON: Go-based TUI client 'axon-shard' not found.")
                print("Please build it first: cd shard && go build -o ../axon-shard.exe")
                return 1

    def is_port_open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', port)) == 0

    # Start backend serve daemon in the background if not already running
    daemon = None
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent)
    
    if not is_port_open(8765):
        print("[AXON] Starting backend daemon...")
        if getattr(sys, 'frozen', False):
            cmd = [sys.argv[0], "repl", "--headless"]
        else:
            cli_path = str(Path(__file__).resolve())
            cmd = [sys.executable, "-u", cli_path, "repl", "--headless"]
            
        log_file = open(str(Path(__file__).parent / "daemon.log"), "w", encoding="utf-8")
        daemon = subprocess.Popen(
            cmd,
            cwd=str(Path(__file__).parent),
            env=env,
            stdout=log_file,
            stderr=log_file
        )
        
        # Wait up to 15 seconds for the port to open
        start_time = time.time()
        while time.time() - start_time < 15.0:
            if is_port_open(8765):
                break
            time.sleep(0.1)

    # Start web dashboard server in background if not already running
    web_daemon = None
    if not is_port_open(3000):
        print("[AXON] Starting web dashboard daemon...")
        if getattr(sys, 'frozen', False):
            web_cmd = [sys.argv[0], "web"]
        else:
            cli_path = str(Path(__file__).resolve())
            web_cmd = [sys.executable, cli_path, "web"]
            
        web_daemon = subprocess.Popen(
            web_cmd,
            cwd=str(Path(__file__).parent),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    try:
        result = subprocess.run([exe_path], check=True)
        return result.returncode
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    except KeyboardInterrupt:
        return 0
    finally:
        if daemon is not None:
            print("\n[AXON] Stopping backend daemon...")
            daemon.terminate()
            try:
                daemon.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                daemon.kill()
        if web_daemon is not None:
            print("[AXON] Stopping web dashboard daemon...")
            web_daemon.terminate()
            try:
                web_daemon.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                web_daemon.kill()


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
            from axon_runtime import ensure_startup_workspace

            ensure_startup_workspace(explicit_cwd=Path(args.cwd))
        except OSError as exc:
            print(f"AXON: invalid --cwd — {exc}", file=sys.stderr)
            return 1
    else:
        try:
            from axon_runtime import ensure_startup_workspace

            ensure_startup_workspace()
        except OSError as exc:
            print(f"AXON: could not set workspace — {exc}", file=sys.stderr)
            return 1

    command = args.command or "tui"

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

    if command == "shard":
        return _run_shard()

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

    if command == "autopilot":
        autopilot_cmd = getattr(args, "autopilot_cmd", None) or "status"
        return _run_autopilot(autopilot_cmd)

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
            cron=getattr(args, "cron", None),
            timer=getattr(args, "timer", None),
            timer_cond=getattr(args, "timer_cond", None),
            cwd=getattr(args, "cwd", None),
        )

    if command == "repl":
        from ui.repl import start_axon

        try:
            asyncio.run(start_axon(headless=getattr(args, "headless", False)))
        except KeyboardInterrupt:
            return 0
        return 0

    parser.error(f"unknown command: {command}")


if __name__ == "__main__":
    sys.exit(main())
