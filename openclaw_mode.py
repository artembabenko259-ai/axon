"""OpenClaw mode — full tool autonomy when elevated + explicitly enabled."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from runtime_policy import load_runtime_policy, save_runtime_policy


def is_process_elevated() -> bool:
    """True when the CLI runs with administrator / root privileges."""
    if sys.platform == "win32":
        try:
            import ctypes

            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    try:
        return os.geteuid() == 0  # type: ignore[attr-defined]
    except AttributeError:
        return False


def is_openclaw_active() -> bool:
    """Policy flag + elevated process (both required)."""
    policy = load_runtime_policy()
    if not policy.openclaw_enabled:
        return False
    return is_process_elevated()


def openclaw_status_lines() -> list[str]:
    policy = load_runtime_policy()
    elevated = is_process_elevated()
    active = is_openclaw_active()
    lines = [
        "OpenClaw — full autonomy (auto-approve write/shell/patch)",
        f"  policy flag:     {'on' if policy.openclaw_enabled else 'off'}",
        f"  elevated admin:  {'yes' if elevated else 'no'}",
        f"  active now:      {'ON' if active else 'off'}",
    ]
    if policy.openclaw_enabled_at:
        lines.append(f"  enabled at:      {policy.openclaw_enabled_at}")
    lines.append("")
    lines.append("  /claw on   — enable (admin terminal required)")
    lines.append("  /claw off  — disable anytime")
    lines.append("  axon claw on|off|status")
    return lines


def enable_openclaw() -> tuple[bool, str]:
    if not is_process_elevated():
        return (
            False,
            "OpenClaw requires an elevated terminal (Run as Administrator on Windows).",
        )
    policy = load_runtime_policy()
    policy.openclaw_enabled = True
    policy.openclaw_enabled_at = datetime.now(timezone.utc).isoformat()
    save_runtime_policy(policy)
    try:
        from audit_log import log_tool_event

        log_tool_event(
            tool="openclaw",
            detail="enabled",
            source="terminal",
            outcome="ok",
        )
    except Exception:
        pass
    return (
        True,
        "OpenClaw ON — AXON will auto-approve dangerous tools in this elevated session.",
    )


def disable_openclaw() -> str:
    policy = load_runtime_policy()
    policy.openclaw_enabled = False
    policy.openclaw_enabled_at = ""
    save_runtime_policy(policy)
    try:
        from audit_log import log_tool_event

        log_tool_event(
            tool="openclaw",
            detail="disabled",
            source="terminal",
            outcome="ok",
        )
    except Exception:
        pass
    return "OpenClaw OFF — tool approval prompts restored."


def handle_claw_arg(action: str) -> tuple[int, str]:
    """CLI: on | off | status."""
    verb = action.strip().lower()
    if verb in {"status", ""}:
        return 0, "\n".join(openclaw_status_lines())
    if verb == "on":
        ok, msg = enable_openclaw()
        return (0 if ok else 1), msg
    if verb == "off":
        return 0, disable_openclaw()
    return 1, "Usage: axon claw on|off|status"
