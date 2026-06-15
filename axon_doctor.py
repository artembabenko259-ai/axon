"""AXON environment diagnostics (`axon doctor`)."""

from __future__ import annotations

import json
import shutil
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from config_store import CONFIG_PATH, get_model, get_openrouter_api_key
from axon_runtime import has_zenith_web, user_data_dir

WS_PORT = 8765


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _check_python() -> CheckResult:
    v = sys.version_info
    ok = v >= (3, 10)
    return CheckResult(
        "python",
        ok,
        f"{v.major}.{v.minor}.{v.micro}" + ("" if ok else " (need 3.10+)"),
    )


def _check_account() -> CheckResult:
    try:
        from axon_auth import load_session

        session = load_session()
    except Exception:
        session = None
    if session:
        return CheckResult("account", True, session.email)
    return CheckResult("account", False, "not signed in — run /login in axon")


def _check_api_key() -> CheckResult:
    key = get_openrouter_api_key()
    if key:
        return CheckResult("api_key", True, "configured")
    if has_zenith_web():
        from zenith_server import config_url

        return CheckResult(
            "api_key",
            False,
            f"missing — open {config_url()} and paste your OpenRouter key",
        )
    return CheckResult(
        "api_key",
        False,
        "missing — set OPENROUTER_API_KEY or edit config.json",
    )


def _check_model() -> CheckResult:
    model = get_model()
    return CheckResult("model", bool(model), model or "not set")


def _check_rg() -> CheckResult:
    rg = shutil.which("rg")
    return CheckResult(
        "ripgrep",
        rg is not None,
        rg or "not on PATH (search_code will use Python fallback)",
    )


def _check_bridge_port() -> CheckResult:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        in_use = sock.connect_ex(("127.0.0.1", WS_PORT)) == 0
    return CheckResult(
        "bridge_port",
        True,
        f"127.0.0.1:{WS_PORT} in use (AXON likely running)"
        if in_use
        else f"127.0.0.1:{WS_PORT} free",
    )


def _check_data_dir() -> CheckResult:
    d = user_data_dir()
    try:
        d.mkdir(parents=True, exist_ok=True)
        ok = d.is_dir()
    except OSError as exc:
        return CheckResult("data_dir", False, str(exc))
    return CheckResult("data_dir", ok, str(d))


def _check_config_path() -> CheckResult:
    return CheckResult("config", CONFIG_PATH.is_file(), str(CONFIG_PATH))


def run_doctor(*, json_output: bool = False, check_updates: bool = False) -> int:
    checks = [
        _check_python(),
        _check_account(),
        _check_api_key(),
        _check_model(),
        _check_config_path(),
        _check_rg(),
        _check_bridge_port(),
        _check_data_dir(),
    ]

    update_line = ""
    if check_updates:
        from version_check import check_for_update

        available, message, _ = check_for_update()
        update_line = message
        if available:
            checks.append(
                CheckResult("update", False, message.replace("\n", " · "))
            )
        else:
            checks.append(CheckResult("update", True, message))

    all_ok = all(c.ok or c.name in {"ripgrep", "update", "account"} for c in checks)

    if json_output:
        print(json.dumps({"ok": all_ok, "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        print("AXON Doctor\n")
        for c in checks:
            mark = "[OK]" if c.ok else "[!!]"
            print(f"  {mark} {c.name}: {c.detail}")
        print()
        if update_line:
            print(update_line)
            print()
        print("All critical checks passed." if all_ok else "Some checks failed.")
        print()
        print("Next steps:")
        if has_zenith_web():
            from zenith_server import config_url, panel_url

            if not get_openrouter_api_key():
                print(f"  axon web --open              Open panel → {panel_url()}")
                print(f"  {config_url()}               Add OpenRouter API key (recommended)")
            else:
                print(f"  axon web --open              Control panel → {panel_url()}")
                print(f"  {config_url()}               Runtime policy & models")
        else:
            print(f"  {CONFIG_PATH}   API key & model")
            print("  axon web --open              Zenith panel (not bundled in this build)")
        print("  axon                         Start the assistant (CLI)")
        print("  axon login                   Sign in at runaxon.xyz (or /login in REPL)")
        if get_openrouter_api_key():
            print(f"  {CONFIG_PATH}   Advanced config")
        print("  axon /help                   All slash commands")

    return 0 if all_ok else 1
