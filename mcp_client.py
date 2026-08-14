from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from axon_runtime import user_data_dir

MCP_CONFIG_PATH = user_data_dir() / "mcp_servers.json"


@dataclass
class McpServer:
    name: str
    command: str
    args: list[str]
    enabled: bool = True


def load_mcp_servers() -> list[McpServer]:
    if not MCP_CONFIG_PATH.is_file():
        return []
    try:
        raw = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    servers: list[McpServer] = []
    for item in raw.get("servers", []):
        if not isinstance(item, dict):
            continue
        servers.append(
            McpServer(
                name=str(item.get("name", "")),
                command=str(item.get("command", "")),
                args=[str(a) for a in item.get("args", [])],
                enabled=bool(item.get("enabled", True)),
            )
        )
    return [s for s in servers if s.name and s.command]


def save_mcp_servers(servers: list[McpServer]) -> Path:
    MCP_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "servers": [
            {
                "name": s.name,
                "command": s.command,
                "args": s.args,
                "enabled": s.enabled,
            }
            for s in servers
        ]
    }
    MCP_CONFIG_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return MCP_CONFIG_PATH


def remove_mcp_server(name: str) -> bool:
    """Remove a persisted (permanent) server by name. Returns False if not found."""
    servers = load_mcp_servers()
    filtered = [s for s in servers if s.name != name]
    if len(filtered) == len(servers):
        return False
    save_mcp_servers(filtered)
    return True


# --- Temporary (session-only) servers ---------------------------------------
# Registered in-memory only — never written to MCP_CONFIG_PATH, so they
# disappear the moment the process (REPL/TUI/daemon) restarts.
_temporary_servers: dict[str, McpServer] = {}


def add_temporary_mcp_server(server: McpServer) -> None:
    _temporary_servers[server.name] = server


def remove_temporary_mcp_server(name: str) -> bool:
    return _temporary_servers.pop(name, None) is not None


def list_temporary_mcp_servers() -> list[McpServer]:
    return list(_temporary_servers.values())


def list_all_mcp_servers() -> list[tuple[McpServer, bool]]:
    """Merged (server, is_temporary) view. A temporary server shadows a
    permanent one of the same name for the rest of the session."""
    merged: dict[str, tuple[McpServer, bool]] = {
        s.name: (s, False) for s in load_mcp_servers()
    }
    for s in _temporary_servers.values():
        merged[s.name] = (s, True)
    return list(merged.values())


def remove_any_mcp_server(name: str) -> str | None:
    """Remove `name` wherever it lives. Returns 'temporary', 'permanent', or
    None if no server with that name was registered."""
    if remove_temporary_mcp_server(name):
        return "temporary"
    if remove_mcp_server(name):
        return "permanent"
    return None


def get_mcp_tool_schemas() -> list[dict[str, Any]]:
    """Placeholder — MCP stdio transport can be wired per-server later."""
    return []
