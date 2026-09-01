"""AXON environment diagnostics (`axon doctor`)."""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import asdict, dataclass

from config_store import CONFIG_PATH, get_model
from provider_config import is_llm_configured, provider_config_hint, provider_label
from axon_runtime import user_data_dir


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
    if is_llm_configured():
        return CheckResult("llm_provider", True, f"{provider_label()} configured")
    return CheckResult(
        "llm_provider",
        False,
        f"missing — {provider_config_hint()}",
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


def _check_hardware() -> CheckResult:
    try:
        from system_info import get_local_model_recommendation
        return CheckResult("hardware_cookbook", True, get_local_model_recommendation())
    except Exception as exc:
        return CheckResult("hardware_cookbook", False, f"failed to check specs: {exc}")


def run_doctor(*, json_output: bool = False, check_updates: bool = False) -> int:
    checks = [
        _check_python(),
        _check_api_key(),
        _check_model(),
        _check_config_path(),
        _check_rg(),
        _check_data_dir(),
        _check_hardware(),
    ]

    all_ok = all(c.ok or c.name in {"ripgrep"} for c in checks)

    if json_output:
        print(json.dumps({"ok": all_ok, "checks": [asdict(c) for c in checks]}, indent=2))
    else:
        print("AXON Doctor\n")
        for c in checks:
            mark = "[OK]" if c.ok else "[!!]"
            print(f"  {mark} {c.name}: {c.detail}")
        print()
        print("All critical checks passed." if all_ok else "Some checks failed.")
        print()
        print("Next steps:")
        print(f"  {CONFIG_PATH}   Provider, API key & model")
        print("  axon                         Start interactive assistant (TUI)")
        print("  axon repl                    Start Rich REPL")
        print("  axon -p \"<prompt>\"           Headless task execution")

    return 0 if all_ok else 1
