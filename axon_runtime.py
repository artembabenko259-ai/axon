"""AXON install/runtime path resolution (dev tree, PyInstaller, Inno Setup)."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "AXON"
PACKAGE_ID = "Core.AXON"
PUBLISHER = "AXON Core Team"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def bundle_root() -> Path:
    """PyInstaller extraction directory (onefile) or source tree root."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent


def install_root() -> Path:
    """Directory containing axon.exe after Inno Setup install."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    """Writable per-user AXON data (config, history)."""
    base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def bundled_axon_dir() -> Path | None:
    """Shipped .axon templates beside the executable or inside the bundle."""
    for candidate in (install_root() / ".axon", bundle_root() / ".axon"):
        if candidate.is_dir():
            return candidate
    return None


def zenith_web_dir() -> Path | None:
    """Bundled Zenith standalone directory, if shipped with the installer."""
    candidate = install_root() / "zenith-web"
    if (candidate / "server.js").is_file():
        return candidate
    return None


def has_zenith_web() -> bool:
    return zenith_web_dir() is not None


def seed_axon_tree(target_workspace: Path) -> None:
    """Copy bundled .axon templates into the user's workspace when missing."""
    source = bundled_axon_dir()
    if source is None:
        return

    target_root = target_workspace / ".axon"
    for rel in ("skills", "docs", "locales"):
        src = source / rel
        if not src.is_dir():
            continue
        dst = target_root / rel
        if dst.exists():
            continue
        shutil.copytree(src, dst)
