"""AXON environment diagnostics (`axon doctor`)."""

from __future__ import annotations

import json
import shutil
import socket
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from config_store import get_openrouter_api_key, get_model
from axon_runtime import user_data_dir

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


def _check_api_key() -> CheckResult:
    key = get_openrouter_api_key()
    return CheckResult(
        "api_key",
        bool(key),
        "configured" if key else "missing — set in config.json or OPENROUTER_API_KEY",
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


def run_doctor(*, json_output: bool = False) -> int:
    checks = [
        _check_python(),
        _check_api_key(),
        _check_model(),
        _check_rg(),
        _check_bridge_port(),
        _check_data_dir(),
    ]
    all_ok = all(c.ok or c.name == "ripgrep" for c in checks)

    if json_output:
        print(json.dumps({"ok": all_ok, "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        print("AXON Doctor\n")
        for c in checks:
            mark = "[OK]" if c.ok else "[!!]"
            print(f"  {mark} {c.name}: {c.detail}")
        print()
        print("All critical checks passed." if all_ok else "Some checks failed.")

    return 0 if all_ok else 1
