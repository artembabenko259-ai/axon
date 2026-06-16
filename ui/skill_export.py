"""Export / share skills from .axon/skills."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from skills_manager import skills_root, sanitize_skill_name


def export_skill(skill_name: str, *, workspace: Path | None = None) -> Path:
    """Copy skill file or folder to .axon/exports/ for sharing."""
    root = skills_root(workspace)
    name = sanitize_skill_name(skill_name)
    if not name:
        raise ValueError("Skill name is required.")

    src_file = root / f"{name}.skill"
    src_dir = root / name
    if src_file.is_file():
        source = src_file
    elif (src_dir / "SKILL.md").is_file():
        source = src_dir
    else:
        raise FileNotFoundError(f"Skill not found: {name}")

    exports = (workspace or Path.cwd()) / ".axon" / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = exports / f"{name}-{stamp}"
    if source.is_file():
        dest = dest.with_suffix(".skill")
        shutil.copy2(source, dest)
    else:
        shutil.copytree(source, dest)
    return dest
