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
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
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


def default_user_workspace() -> Path:
    """Sensible folder when AXON must not use the install directory."""
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        return desktop.resolve()
    return Path.home().resolve()


def is_axon_install_cwd(cwd: Path) -> bool:
    """True when the process cwd is the shipped axon.exe directory (not user project)."""
    if not is_frozen():
        return False
    try:
        return cwd.resolve() == install_root().resolve()
    except OSError:
        return False


def get_last_workspace() -> Path | None:
    from config_store import load_config

    raw = (load_config().get("last_workspace") or "").strip()
    if not raw:
        return None
    path = Path(raw)
    try:
        if path.is_dir():
            return path.resolve()
    except OSError:
        return None
    return None


def save_last_workspace(path: Path) -> None:
    from config_store import save_config

    try:
        resolved = path.resolve()
    except OSError:
        return
    save_config({"last_workspace": str(resolved)})


def resolve_startup_cwd(*, explicit_cwd: Path | None = None) -> Path:
    """Pick a user project directory instead of the AXON install folder."""
    if explicit_cwd is not None:
        workspace = explicit_cwd.expanduser().resolve()
        save_last_workspace(workspace)
        return workspace

    cwd = Path.cwd()
    try:
        resolved = cwd.resolve()
    except OSError:
        resolved = cwd

    if not is_axon_install_cwd(resolved):
        save_last_workspace(resolved)
        return resolved

    last = get_last_workspace()
    if last is not None:
        return last

    workspace = default_user_workspace()
    save_last_workspace(workspace)
    return workspace


def ensure_startup_workspace(*, explicit_cwd: Path | None = None) -> Path:
    """chdir to the resolved workspace and seed bundled .axon templates."""
    workspace = resolve_startup_cwd(explicit_cwd=explicit_cwd)
    os.chdir(workspace)
    seed_axon_tree(workspace)
    return workspace
