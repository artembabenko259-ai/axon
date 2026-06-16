"""Dynamic plugins from `.axon/plugins/` (Python modules)."""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

PLUGIN_ENTRY = "register"


@dataclass
class AxonPlugin:
    name: str
    path: Path
    module: ModuleType
    commands: dict[str, Callable[..., Any]]

    def run(self, command: str, *args: str) -> Any:
        handler = self.commands.get(command)
        if handler is None:
            raise KeyError(f"Plugin {self.name} has no command {command!r}")
        return handler(*args)


def plugins_dir(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / ".axon" / "plugins"


def _load_module(path: Path) -> ModuleType | None:
    name = f"axon_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover_plugins(workspace: Path | None = None) -> list[AxonPlugin]:
    root = plugins_dir(workspace)
    if not root.is_dir():
        return []

    loaded: list[AxonPlugin] = []
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _load_module(path)
        except Exception:
            continue
        if module is None or not hasattr(module, PLUGIN_ENTRY):
            continue
        register = getattr(module, PLUGIN_ENTRY)
        if not callable(register):
            continue
        try:
            commands = register() or {}
        except Exception:
            continue
        if not isinstance(commands, dict):
            continue
        loaded.append(
            AxonPlugin(
                name=path.stem,
                path=path,
                module=module,
                commands=commands,
            )
        )
    return loaded


def list_plugin_commands(workspace: Path | None = None) -> dict[str, str]:
    """Map slash-style names to descriptions for /help."""
    out: dict[str, str] = {}
    for plugin in discover_plugins(workspace):
        for cmd, handler in plugin.commands.items():
            doc = getattr(handler, "__doc__", "") or f"Plugin {plugin.name}"
            out[f"/{cmd.lstrip('/')}"] = doc.strip().split("\n", 1)[0]
    return out
