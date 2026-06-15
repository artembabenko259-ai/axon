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
    web_dir = ROOT / "zenith-web"
    if not (web_dir / "package.json").is_file():
        print("AXON: zenith-web not found.", file=sys.stderr)
        return 1

    if open_browser:
        import threading
        import time
        import webbrowser

        def _open() -> None:
            time.sleep(2.5)
            webbrowser.open(f"http://localhost:{port}")

        threading.Thread(target=_open, daemon=True).start()

    try:
        return subprocess.call(
            ["npm", "run", "dev", "--", "-p", str(port)],
            cwd=str(web_dir),
            shell=sys.platform == "win32",
        )
    except OSError as exc:
        print(f"AXON: could not start web server — {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.prompt is None and not sys.stdin.isatty():
        args.prompt = sys.stdin.read()

    if args.cwd:
        try:
            import os

            os.chdir(args.cwd)
        except OSError as exc:
            print(f"AXON: invalid --cwd — {exc}", file=sys.stderr)
            return 1

    if args.prompt:
        from ui.headless import run_headless

        return run_headless(
            args.prompt,
            model=args.model,
            json_output=args.json,
            auto_approve=args.yes,
        )

    command = args.command or "repl"

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

    from ui.repl import start_axon

    try:
        asyncio.run(start_axon())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
