from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from pathlib import Path

from axon_runtime import user_data_dir

POLICY_PATH = user_data_dir() / "runtime_policy.json"

DEFAULT_TOOL_POLICY: dict[str, str] = {
    "read_file": "auto",
    "list_dir": "auto",
    "glob_files": "auto",
    "search_code": "auto",
    "web_search": "auto",
    "write_file": "ask",
    "execute_shell": "ask",
    "apply_patch": "ask",
}


@dataclass
class RuntimePolicy:
    """Local runtime controls — editable via localhost web UI or CLI."""

    # Full autonomy: auto-approve write_file + execute_shell
    autonomy_enabled: bool = False
    # Allow web dashboard to send commands (requires bridge token)
    web_control_enabled: bool = True
    # Allow terminal REPL (always true in practice when CLI runs)
    terminal_control_enabled: bool = True
    # Web/LAN requests must confirm dangerous ops in the PC terminal
    require_desktop_confirmation: bool = True
    # Run multiple agent tasks concurrently (web + terminal)
    allow_parallel_agents: bool = False
    # Require token on WebSocket connect (recommended)
    bridge_auth_enabled: bool = True
    # Secret token — auto-generated, shown in terminal + /config
    bridge_token: str = ""
    # Short PIN for pairing display (optional extra check)
    bridge_pin: str = ""
    tool_policy: dict[str, str] = field(default_factory=dict)

    def resolved_tool_policy(self) -> dict[str, str]:
        merged = dict(DEFAULT_TOOL_POLICY)
        merged.update(self.tool_policy or {})
        return merged

    def tool_mode(self, tool_name: str) -> str:
        return self.resolved_tool_policy().get(tool_name, "ask")

    def ensure_secrets(self) -> None:
        if not self.bridge_token:
            self.bridge_token = secrets.token_urlsafe(24)
        if not self.bridge_pin:
            self.bridge_pin = f"{secrets.randbelow(900000) + 100000:06d}"


def _default_policy() -> RuntimePolicy:
    policy = RuntimePolicy()
    policy.ensure_secrets()
    return policy


def load_runtime_policy() -> RuntimePolicy:
    if not POLICY_PATH.is_file():
        policy = _default_policy()
        save_runtime_policy(policy)
        return policy

    try:
        raw = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        policy = _default_policy()
        save_runtime_policy(policy)
        return policy

    policy = RuntimePolicy(
        autonomy_enabled=bool(raw.get("autonomy_enabled", False)),
        web_control_enabled=bool(raw.get("web_control_enabled", True)),
        terminal_control_enabled=bool(raw.get("terminal_control_enabled", True)),
        require_desktop_confirmation=bool(
            raw.get("require_desktop_confirmation", True)
        ),
        allow_parallel_agents=bool(raw.get("allow_parallel_agents", False)),
        bridge_auth_enabled=bool(raw.get("bridge_auth_enabled", True)),
        bridge_token=str(raw.get("bridge_token", "")),
        bridge_pin=str(raw.get("bridge_pin", "")),
        tool_policy={
            str(k): str(v)
            for k, v in (raw.get("tool_policy") or {}).items()
            if str(v) in {"auto", "ask", "deny"}
        },
    )
    if policy.bridge_auth_enabled:
        policy.ensure_secrets()
        save_runtime_policy(policy)
    return policy


def save_runtime_policy(policy: RuntimePolicy) -> Path:
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if policy.bridge_auth_enabled:
        policy.ensure_secrets()
    payload = asdict(policy)
    POLICY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return POLICY_PATH


def policy_for_client() -> dict[str, object]:
    """Safe subset for web UI (includes token for localhost pairing)."""
    policy = load_runtime_policy()
    return {
        "autonomy_enabled": policy.autonomy_enabled,
        "web_control_enabled": policy.web_control_enabled,
        "terminal_control_enabled": policy.terminal_control_enabled,
        "require_desktop_confirmation": policy.require_desktop_confirmation,
        "allow_parallel_agents": policy.allow_parallel_agents,
        "bridge_auth_enabled": policy.bridge_auth_enabled,
        "bridge_token": policy.bridge_token,
        "bridge_pin": policy.bridge_pin,
        "tool_policy": policy.resolved_tool_policy(),
        "policy_path": str(POLICY_PATH),
    }


def verify_bridge_token(token: str) -> bool:
    policy = load_runtime_policy()
    if not policy.bridge_auth_enabled:
        return True
    expected = policy.bridge_token.strip()
    if not expected:
        return False
    return secrets.compare_digest(token.strip(), expected)
