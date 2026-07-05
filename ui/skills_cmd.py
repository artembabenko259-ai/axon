"""REPL `/skills` command — manage active/disabled skill integrations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from config_store import load_config, save_config
from skills_manager import skills_root, parse_skill_file

Emit = Callable[[Any], Awaitable[None]]


def get_all_skills_on_disk(workspace: Path | None = None) -> list[dict[str, Any]]:
    root = skills_root(workspace)
    if not root.is_dir():
        return []

    config = load_config()
    disabled_skills = set(config.get("disabled_skills", []) or [])

    found: dict[str, dict[str, Any]] = {}

    def add_skill(skill):
        if not skill:
            return
        is_enabled = not (
            skill.name in disabled_skills or
            skill.skill_id in disabled_skills or
            skill.tool_name in disabled_skills
        )
        found[skill.tool_name] = {
            "name": skill.name,
            "description": skill.description,
            "is_enabled": is_enabled,
            "id": skill.skill_id,
            "tool_name": skill.tool_name
        }

    # 1. Directory skills
    for skill_dir in sorted(root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.is_file():
            add_skill(parse_skill_file(skill_file))

    # 2. File skills
    for skill_file in sorted(root.glob("*.skill")):
        if skill_file.is_file():
            add_skill(parse_skill_file(skill_file))

    return list(found.values())


async def handle_skills_command(stripped: str, *, llm_manager: Any, emit: Emit) -> bool:
    if not stripped.lower().startswith("/skills"):
        return False

    parts = stripped.split(maxsplit=2)
    sub = parts[1].lower() if len(parts) > 1 else ""

    if sub in {"", "list", "show"}:
        skills = get_all_skills_on_disk(llm_manager.workspace)
        if not skills:
            await emit("[dim]No skills found in .axon/skills/[/dim]\n")
            return True

        lines = ["[bold]AXON Custom Skills (Integrations):[/bold]", ""]
        for s in skills:
            status = "[green][Enabled][/green]" if s["is_enabled"] else "[red][Disabled][/red]"
            lines.append(f"  {status} [cyan]{s['name']:<22}[/] - {s['description']}")

        lines.extend(
            [
                "",
                "[dim]Use `/skills enable <name>` to enable an integration.[/]",
                "[dim]Use `/skills disable <name>` to disable an integration (saves context and api keys).[/]",
            ]
        )
        await emit("\n".join(lines) + "\n")
        return True

    if sub == "enable":
        if len(parts) < 3:
            await emit("[yellow]Usage: /skills enable <skill_name>[/]\n")
            return True
        name = parts[2].strip()
        skills = get_all_skills_on_disk(llm_manager.workspace)
        matched = [s for s in skills if s["name"].lower() == name.lower() or s["tool_name"].lower() == name.lower()]
        if not matched:
            await emit(f"[red]Skill '{name}' not found.[/]\n")
            return True

        target = matched[0]
        config = load_config()
        disabled = list(config.get("disabled_skills", []) or [])
        # Remove all possible variations from disabled list
        disabled = [d for d in disabled if d.lower() not in {target["name"].lower(), target["id"].lower(), target["tool_name"].lower()}]
        save_config({"disabled_skills": disabled})
        
        # Force reload in LLMManager
        llm_manager.reload_skills()
        await emit(f"[green][✓] Skill '{target['name']}' has been enabled.[/]\n")
        return True

    if sub == "disable":
        if len(parts) < 3:
            await emit("[yellow]Usage: /skills disable <skill_name>[/]\n")
            return True
        name = parts[2].strip()
        skills = get_all_skills_on_disk(llm_manager.workspace)
        matched = [s for s in skills if s["name"].lower() == name.lower() or s["tool_name"].lower() == name.lower()]
        if not matched:
            await emit(f"[red]Skill '{name}' not found.[/]\n")
            return True

        target = matched[0]
        config = load_config()
        disabled = list(config.get("disabled_skills", []) or [])
        if target["name"] not in disabled:
            disabled.append(target["name"])
        save_config({"disabled_skills": disabled})

        # Force reload in LLMManager
        llm_manager.reload_skills()
        await emit(f"[green][✓] Skill '{target['name']}' has been disabled (will not be exposed to the LLM).[/]\n")
        return True

    await emit("[yellow]Usage: /skills | /skills enable <name> | /skills disable <name>[/]\n")
    return True
