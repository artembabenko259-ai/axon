"""UAR — Utility Axon Registry: a mini package manager for AXON skills."""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

REGISTRY_URL = "https://raw.githubusercontent.com/artembabenko259-ai/axon/main/registry/skills.json"
SKILLS_BASE_URL = "https://raw.githubusercontent.com/artembabenko259-ai/axon/main/registry/skills/"


def find_workspace_root() -> Path:
    # Scan upwards from current working directory to find a folder containing '.axon'
    curr = Path.cwd().resolve()
    for parent in [curr] + list(curr.parents):
        if (parent / ".axon").is_dir():
            return parent
    return curr


def get_skills_dir() -> Path:
    root = find_workspace_root()
    path = root / ".axon" / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def fetch_registry() -> dict:
    try:
        req = urllib.request.Request(
            REGISTRY_URL,
            headers={"User-Agent": "UAR-Client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"Error: Failed to fetch remote registry from GitHub: {exc}")
        sys.exit(1)


def cmd_list() -> None:
    try:
        registry = fetch_registry()
    except Exception:
        registry = {}
        
    if "axon-dart" not in registry:
        registry["axon-dart"] = {
            "filename": "axon-dart.skill",
            "description": "AI-assisted reverse engineering helper. Analyze binaries, decompile functions, and explain binary code."
        }
        
    skills_dir = get_skills_dir()
    
    print("UAR — Available Skills in Registry:")
    print("=" * 70)
    
    for name, info in sorted(registry.items()):
        filename = info.get("filename", f"{name}.skill")
        installed = (skills_dir / filename).is_file() or (skills_dir / name / "SKILL.md").is_dir()
        status = "[Installed]" if installed else "[Not Installed]"
        desc = info.get("description", "")
        print(f"  {name:<22} {status:<16} - {desc}")
    print("=" * 70)


def cmd_get(skill_name: str) -> None:
    clean_name = skill_name
    if clean_name.endswith(".skill"):
        clean_name = clean_name[:-6]

    skills_dir = get_skills_dir()
    dest = skills_dir / f"{clean_name}.skill"

    if clean_name.lower() == "axon-dart":
        print(f"Installing '{clean_name}' from built-in registry...")
        content = """---
name: axon-dart
description: AI-assisted reverse engineering helper. Analyze binaries, decompile functions, and explain binary code.
allowed-tools: execute_shell, read_file
---

# AXON Dart: Reverse Engineering Skill

You are now equipped with AXON Dart capabilities for reverse engineering target binaries.

## Workflow
1. Analyze a binary: Check if Radare2 (r2) is installed via `r2 -v`.
2. Run standard commands to get symbols: `r2 -q -c "afl" <binary_path>`.
3. Disassemble a function: `r2 -q -c "pdf @ <function_name>" <binary_path>`.
4. Analyze pseudo-code or assembly to explain logic, find vulnerabilities, and rename symbols.
"""
        dest.write_text(content, encoding="utf-8")
        print(f"Successfully installed skill '{clean_name}' to {dest}")
        return

    registry = fetch_registry()
    if clean_name not in registry:
        print(f"Error: Skill '{skill_name}' not found in registry.")
        print("Run 'uar list' to see available skills.")
        sys.exit(1)

    info = registry[clean_name]
    filename = info.get("filename", f"{clean_name}.skill")
    url = SKILLS_BASE_URL + filename
    
    print(f"Downloading '{clean_name}' from GitHub...")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "UAR-Client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
            
        dest.write_bytes(data)
        print(f"Successfully installed skill '{clean_name}' to {dest}")
    except Exception as exc:
        print(f"Error: Failed to download skill: {exc}")
        sys.exit(1)


def cmd_remove(skill_name: str) -> None:
    skills_dir = get_skills_dir()
    
    clean_name = skill_name
    if clean_name.endswith(".skill"):
        clean_name = clean_name[:-6]
        
    file_path = skills_dir / f"{clean_name}.skill"
    dir_path = skills_dir / clean_name
    
    removed = False
    if file_path.is_file():
        file_path.unlink()
        removed = True
    if dir_path.is_dir():
        shutil.rmtree(dir_path)
        removed = True
        
    if removed:
        print(f"Successfully removed skill '{clean_name}' from workspace.")
    else:
        print(f"Error: Skill '{skill_name}' is not installed in the current workspace.")


def main() -> None:
    if len(sys.argv) < 2:
        print("UAR — Utility Axon Registry (Skills Package Manager)")
        print()
        print("Usage:")
        print("  uar list                 - List available skills in the remote registry")
        print("  uar get -S <skill_name>  - Install a skill from the registry")
        print("  uar remove <skill_name>  - Uninstall/remove a skill from workspace")
        sys.exit(0)
        
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        cmd_list()
    elif cmd == "get":
        if len(sys.argv) < 4 or sys.argv[2] != "-S":
            print("Error: Missing arguments for 'get'. Use: uar get -S <skill_name>")
            sys.exit(1)
        cmd_get(sys.argv[3])
    elif cmd == "remove":
        if len(sys.argv) < 3:
            print("Error: Missing skill name for 'remove'. Use: uar remove <skill_name>")
            sys.exit(1)
        cmd_remove(sys.argv[2])
    else:
        print(f"Error: Unknown command '{cmd}'.")
        sys.exit(1)


if __name__ == "__main__":
    main()
