from __future__ import annotations

import re
from pathlib import Path

AGENTS_DIR_NAME = ".axon/agents"
TOOL_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")

DEFAULT_AGENT_PROMPT = """# {title} Agent

You are a specialized sub-agent of AXON focused on: {focus}

## Your mission
{mission}

## Rules
1. Use read_file, write_file, execute_shell, and web_search when needed.
2. write_file and execute_shell require user approval — respect denials.
3. Stay within your specialty; defer unrelated work to the main AXON agent.
4. Reply in clear, actionable language.
"""


def agents_root(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".axon" / "agents"


def sanitize_agent_name(name: str) -> str:
    cleaned = TOOL_NAME_PATTERN.sub("-", name.strip().lower()).strip("-")
    return cleaned or "custom-agent"


def agent_dir(name: str, workspace: Path | None = None) -> Path:
    return agents_root(workspace) / sanitize_agent_name(name)


def agent_prompt_path(name: str, workspace: Path | None = None) -> Path:
    return agent_dir(name, workspace) / "system_prompt.md"


def ensure_agents_workspace(workspace: Path | None = None) -> Path:
    root = agents_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    return root


def list_agents(workspace: Path | None = None) -> list[str]:
    root = agents_root(workspace)
    if not root.is_dir():
        return []
    agents: list[str] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and (entry / "system_prompt.md").is_file():
            agents.append(entry.name)
    return agents


def load_agent_prompt(name: str, workspace: Path | None = None) -> str | None:
    path = agent_prompt_path(name, workspace)
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        return text or None
    except OSError:
        return None


def create_agent(
    name: str,
    focus: str,
    mission: str = "",
    *,
    workspace: Path | None = None,
) -> Path:
    """Create `.axon/agents/<name>/system_prompt.md`."""
    ensure_agents_workspace(workspace)
    agent_name = sanitize_agent_name(name)
    directory = agent_dir(agent_name, workspace)
    directory.mkdir(parents=True, exist_ok=True)
    prompt_path = directory / "system_prompt.md"

    title = agent_name.replace("-", " ").title()
    focus_text = focus.strip() or "general assistance"
    mission_text = mission.strip() or f"Help the user with {focus_text}."

    content = DEFAULT_AGENT_PROMPT.format(
        title=title,
        focus=focus_text,
        mission=mission_text,
    )
    prompt_path.write_text(content, encoding="utf-8")
    return prompt_path
