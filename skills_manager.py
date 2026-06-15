from __future__ import annotations

import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILLS_DIR_NAME = ".axon/skills"
INLINE_SHELL_PATTERN = re.compile(r"!`([^`]+)`")
SHELL_TIMEOUT_SECONDS = 30
MAX_INLINE_OUTPUT = 16_384
TOOL_NAME_PATTERN = re.compile(r"[^a-zA-Z0-9_-]")

README_CONTENT = """# AXON Skills

Skills are markdown-driven instruction sets (inspired by Claude Code's `SKILL.md`).

## Layout

```
.axon/skills/
  my-skill/
    SKILL.md
```

Each skill lives in its own subdirectory with a `SKILL.md` file.

## SKILL.md format

```markdown
---
name: my-skill
description: Short description shown to the LLM as a tool
disable-model-invocation: false
allowed-tools: read_file, execute_shell
---

# Instructions

Your skill body here. Use inline shell to inject live context:

Current directory:
!`pwd`

When this skill is invoked, follow the instructions above.
```

## Frontmatter fields

| Field | Description |
|-------|-------------|
| `name` | Tool name (defaults to folder name) |
| `description` | Tool description for the LLM |
| `disable-model-invocation` | If `true`, hidden from LLM tools (manual only) |
| `allowed-tools` | Comma-separated built-in tools the skill may use |

## Inline shell (`!`command``)

Before the skill body is sent to the LLM, AXON executes `!`command`` placeholders
locally and replaces them with stdout/stderr output.
"""

EXAMPLE_SKILL_CONTENT = """---
name: git-status
description: Inspect git repository status and summarize recent activity for the user
disable-model-invocation: false
allowed-tools: execute_shell, read_file
---

# Git Status Skill

You are helping the user understand their git repository.

## Live context (auto-injected)

Branch:
!`git branch --show-current 2>nul || git branch --show-current`

Last 3 commits:
!`git log -3 --oneline 2>nul || git log -3 --oneline`

## Instructions

1. Run or reason about `git status` using `execute_shell` if needed.
2. Summarize staged, unstaged, and untracked changes clearly.
3. Mention the current branch and recent commits from the context above.
4. Keep the reply concise and actionable.
"""


@dataclass(frozen=True)
class Skill:
    """A loaded markdown skill from `.axon/skills/<id>/SKILL.md`."""

    skill_id: str
    name: str
    description: str
    disable_model_invocation: bool
    allowed_tools: tuple[str, ...]
    body_raw: str
    path: Path

    @property
    def tool_name(self) -> str:
        return sanitize_tool_name(self.name)


def sanitize_tool_name(name: str) -> str:
    cleaned = TOOL_NAME_PATTERN.sub("_", name.strip()).strip("_")
    return cleaned or "skill"


def skills_root(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".axon" / "skills"


def project_memory_path(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".axon" / "memory.md"


def load_project_memory(workspace: Path | None = None) -> str:
    """Read `.axon/memory.md` for invisible project context injection."""
    path = project_memory_path(workspace)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def ensure_skills_workspace(workspace: Path | None = None) -> Path:
    """Create `.axon/skills/` with README and an example skill if missing."""
    root = skills_root(workspace)
    root.mkdir(parents=True, exist_ok=True)

    readme = root / "README.md"
    if not readme.exists():
        readme.write_text(README_CONTENT, encoding="utf-8")

    example_dir = root / "git-status"
    example_skill = example_dir / "SKILL.md"
    if not example_skill.exists():
        example_dir.mkdir(parents=True, exist_ok=True)
        example_skill.write_text(EXAMPLE_SKILL_CONTENT, encoding="utf-8")

    return root


def sanitize_skill_name(name: str) -> str:
    cleaned = TOOL_NAME_PATTERN.sub("-", name.strip().lower()).strip("-")
    return cleaned or "custom-skill"


def extract_skill_code_block(text: str) -> str:
    """Pull skill file content from an LLM response (fenced block or raw frontmatter)."""
    stripped = text.strip()
    if not stripped:
        return ""

    fence = re.search(
        r"```(?:skill|markdown|yaml|md|txt)?\s*\n(.*?)```",
        stripped,
        re.DOTALL | re.IGNORECASE,
    )
    if fence:
        return fence.group(1).strip()

    if stripped.startswith("---"):
        return stripped

    return stripped


def skill_name_from_content(content: str, *, fallback: str = "custom-skill") -> str:
    """Read and sanitize `name` from generated skill frontmatter."""
    meta, _ = parse_frontmatter(content)
    raw_name = str(meta.get("name") or "").strip()
    return sanitize_skill_name(raw_name or fallback)


def save_generated_skill_file(
    content: str,
    *,
    workspace: Path | None = None,
) -> tuple[Path, str]:
    """Write LLM output to `.axon/skills/<skill_name>.skill`."""
    ensure_skills_workspace(workspace)
    skill_content = extract_skill_code_block(content)
    if not skill_content.strip():
        raise ValueError("Generated skill content is empty.")

    meta, _ = parse_frontmatter(skill_content)
    if not str(meta.get("name") or "").strip():
        raise ValueError("Generated skill must include a `name` field in YAML frontmatter.")

    skill_name = skill_name_from_content(skill_content)
    skill_path = skills_root(workspace) / f"{skill_name}.skill"
    skill_path.write_text(skill_content.rstrip() + "\n", encoding="utf-8")
    return skill_path, skill_name


def parse_gen_skill_description(command_line: str) -> str | None:
    """Parse `/gen-skill <description>` supporting quoted descriptions."""
    stripped = command_line.strip()
    if not stripped.lower().startswith("/gen-skill"):
        return None

    rest = stripped[len("/gen-skill") :].strip()
    if not rest:
        return None

    if rest[0] in "\"'":
        quote = rest[0]
        end = rest.find(quote, 1)
        if end == -1:
            return rest[1:].strip()
        return rest[1:end].strip()

    return rest.strip()


def create_skill_file(
    name: str,
    description: str,
    shell_command: str = "",
    *,
    workspace: Path | None = None,
) -> Path:
    """Write a new `.axon/skills/<name>/SKILL.md` from wizard inputs."""
    ensure_skills_workspace(workspace)
    skill_name = sanitize_skill_name(name)
    skill_dir = skills_root(workspace) / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path = skill_dir / "SKILL.md"

    body_lines = [
        f"# {skill_name.replace('-', ' ').title()}",
        "",
        description.strip() or "Follow the instructions below.",
        "",
    ]
    if shell_command.strip():
        body_lines.extend(
            [
                "## Live context (auto-injected)",
                "",
                f"!`{shell_command.strip()}`",
                "",
            ]
        )
    body_lines.extend(
        [
            "## Instructions",
            "",
            "1. Understand the user's request.",
            "2. Use allowed tools as needed.",
            "3. Respond with a clear, actionable summary.",
        ]
    )

    content = (
        "---\n"
        f"name: {skill_name}\n"
        f"description: {description.strip() or f'Run the {skill_name} skill'}\n"
        "disable-model-invocation: false\n"
        "allowed-tools: read_file, execute_shell\n"
        "---\n\n"
        + "\n".join(body_lines)
        + "\n"
    )
    skill_path.write_text(content, encoding="utf-8")
    return skill_path


def parse_skill_file(path: Path) -> Skill | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None

    meta, body = parse_frontmatter(raw)
    if path.name == "SKILL.md":
        skill_id = path.parent.name
    elif path.suffix == ".skill":
        skill_id = path.stem
    else:
        skill_id = path.stem

    name = str(meta.get("name") or skill_id).strip()
    description = str(
        meta.get("description") or f"Invoke the {name} skill"
    ).strip()
    disable = _parse_bool(meta.get("disable-model-invocation", False))
    allowed = _parse_allowed_tools(meta.get("allowed-tools", ""))

    return Skill(
        skill_id=skill_id,
        name=name,
        description=description,
        disable_model_invocation=disable,
        allowed_tools=allowed,
        body_raw=body,
        path=path,
    )


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML-like frontmatter and markdown body."""
    stripped = text.lstrip("\ufeff")
    if not stripped.startswith("---"):
        return {}, stripped

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?", stripped, re.DOTALL)
    if not match:
        return {}, stripped

    frontmatter = match.group(1)
    body = stripped[match.end() :]
    return _parse_simple_yaml(frontmatter), body


def _parse_simple_yaml(block: str) -> dict[str, Any]:
    """Minimal YAML parser for SKILL.md frontmatter (no external dependency)."""
    result: dict[str, Any] = {}
    current_key: str | None = None
    list_items: list[str] = []

    for line in block.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_key:
            list_items.append(stripped[2:].strip().strip('"').strip("'"))
            continue

        if current_key and list_items:
            result[current_key] = list_items
            list_items = []
            current_key = None

        if ":" not in stripped:
            continue

        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if not value:
            current_key = key
            list_items = []
            continue

        if value.lower() in {"true", "false"}:
            result[key] = value.lower() == "true"
        elif "," in value:
            result[key] = [part.strip() for part in value.split(",") if part.strip()]
        else:
            result[key] = value

    if current_key and list_items:
        result[current_key] = list_items

    return result


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _parse_allowed_tools(value: Any) -> tuple[str, ...]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return tuple(items)
    if not value:
        return ()
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def run_inline_shell(command: str) -> str:
    """Execute a shell command for `!`cmd`` injection (no user approval)."""
    cmd = command.strip()
    if not cmd:
        return "(empty command)"

    try:
        if sys.platform == "win32":
            proc = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )
        else:
            proc = subprocess.run(
                shlex.split(cmd),
                capture_output=True,
                text=True,
                timeout=SHELL_TIMEOUT_SECONDS,
            )
    except subprocess.TimeoutExpired:
        return f"(command timed out after {SHELL_TIMEOUT_SECONDS}s)"
    except Exception as exc:
        return f"(command error: {exc})"

    parts: list[str] = []
    if proc.stdout:
        parts.append(proc.stdout.rstrip())
    if proc.stderr:
        parts.append(proc.stderr.rstrip())

    output = "\n".join(parts).strip()
    if not output:
        return f"(no output, exit code {proc.returncode})"
    if len(output) > MAX_INLINE_OUTPUT:
        output = f"{output[:MAX_INLINE_OUTPUT]}\n… (truncated)"
    return output


def inject_shell_context(body: str) -> str:
    """Replace all `!`command`` placeholders with local shell stdout."""

    def _replace(match: re.Match[str]) -> str:
        return run_inline_shell(match.group(1))

    return INLINE_SHELL_PATTERN.sub(_replace, body)


@dataclass
class SkillManager:
    """Scan, parse, and invoke markdown skills from `.axon/skills/`."""

    workspace: Path = field(default_factory=Path.cwd)
    _skills: dict[str, Skill] = field(default_factory=dict, init=False)
    _by_tool_name: dict[str, Skill] = field(default_factory=dict, init=False)

    def reload(self) -> int:
        self._skills.clear()
        self._by_tool_name.clear()

        root = skills_root(self.workspace)
        if not root.is_dir():
            return 0

        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            skill = parse_skill_file(skill_file)
            if skill is None:
                continue
            self._skills[skill.skill_id] = skill
            self._by_tool_name[skill.tool_name] = skill

        for skill_file in sorted(root.glob("*.skill")):
            if not skill_file.is_file():
                continue
            skill = parse_skill_file(skill_file)
            if skill is None:
                continue
            self._skills[skill.skill_id] = skill
            self._by_tool_name[skill.tool_name] = skill

        return len(self._skills)

    @property
    def skills(self) -> dict[str, Skill]:
        return dict(self._skills)

    def is_skill_tool(self, tool_name: str) -> bool:
        return tool_name in self._by_tool_name

    def get_skill(self, tool_name: str) -> Skill | None:
        return self._by_tool_name.get(tool_name)

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        schemas: list[dict[str, Any]] = []
        for skill in self._skills.values():
            if skill.disable_model_invocation:
                continue
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": skill.tool_name,
                        "description": skill.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "request": {
                                    "type": "string",
                                    "description": (
                                        "Optional user request or extra context "
                                        "for this skill"
                                    ),
                                },
                            },
                        },
                    },
                }
            )
        return schemas

    def invoke_skill(self, tool_name: str, arguments: dict[str, Any]) -> str:
        skill = self.get_skill(tool_name)
        if skill is None:
            return f"Error: unknown skill '{tool_name}'."

        resolved_body = inject_shell_context(skill.body_raw)
        user_request = str(arguments.get("request", "")).strip()
        allowed = ", ".join(skill.allowed_tools) if skill.allowed_tools else "all built-in tools"

        sections = [
            f"# Skill activated: {skill.name}",
            "",
            "Follow the instructions below strictly. Use built-in tools "
            f"({allowed}) as needed to complete the task.",
            "",
            "## Skill instructions",
            "",
            resolved_body.strip(),
        ]

        if user_request:
            sections.extend(["", "## User request", "", user_request])

        return "\n".join(sections)

    def skills_summary_for_system(self) -> str:
        invocable = [
            skill for skill in self._skills.values() if not skill.disable_model_invocation
        ]
        if not invocable:
            return ""
        lines = ["Available markdown skills (invoke via tool call):"]
        for skill in invocable:
            tools = ", ".join(skill.allowed_tools) if skill.allowed_tools else "default"
            lines.append(f"- {skill.tool_name}: {skill.description} (tools: {tools})")
        return "\n".join(lines)
