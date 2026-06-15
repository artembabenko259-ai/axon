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


def get_mcp_tool_schemas() -> list[dict[str, Any]]:
    """Placeholder — MCP stdio transport can be wired per-server later."""
    return []
