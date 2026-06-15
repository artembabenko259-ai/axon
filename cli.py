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

    web = sub.add_parser("web", help="Start Zenith web dashboard (dev server)")
    web.add_argument("--port", type=int, default=3000)

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


def _run_doctor(*, json_output: bool) -> int:
    from axon_doctor import run_doctor

    return run_doctor(json_output=json_output)


def _run_web(port: int) -> int:
    web_dir = ROOT / "zenith-web"
    if not (web_dir / "package.json").is_file():
        print("AXON: zenith-web not found.", file=sys.stderr)
        return 1
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
        return _run_doctor(json_output=args.json)

    if command == "web":
        return _run_web(args.port)

    from ui.repl import start_axon

    try:
        asyncio.run(start_axon())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
