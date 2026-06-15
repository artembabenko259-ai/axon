"""Launch bundled Zenith (Next.js standalone) from the AXON installer."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from axon_runtime import install_root

DEFAULT_ZENITH_PORT = 3000


def panel_url(port: int = DEFAULT_ZENITH_PORT) -> str:
    return f"http://127.0.0.1:{port}"


def config_url(port: int = DEFAULT_ZENITH_PORT) -> str:
    return f"{panel_url(port)}/config"


def bundled_zenith_dir() -> Path | None:
    """Production Zenith standalone next to axon.exe."""
    candidate = install_root() / "zenith-web"
    if (candidate / "server.js").is_file():
        return candidate
    return None


def dev_zenith_dir() -> Path | None:
    """Source zenith-web tree for npm run dev."""
    for base in (install_root(), Path(__file__).resolve().parent):
        candidate = base / "zenith-web"
        if (candidate / "package.json").is_file() and not (candidate / "server.js").is_file():
            return candidate
    return None


def has_bundled_zenith() -> bool:
    return bundled_zenith_dir() is not None


def resolve_node_exe() -> Path | None:
    bundled = install_root() / "node" / "node.exe"
    if bundled.is_file():
        return bundled
    import shutil

    found = shutil.which("node")
    return Path(found) if found else None


def _server_env(port: int) -> dict[str, str]:
    env = os.environ.copy()
    env["PORT"] = str(port)
    env["HOSTNAME"] = "127.0.0.1"
    return env


def run_zenith_foreground(port: int = DEFAULT_ZENITH_PORT) -> int:
    app_dir = bundled_zenith_dir()
    node = resolve_node_exe()
    if not app_dir or not node:
        print("AXON: bundled Zenith panel not found.", file=sys.stderr)
        print("AXON: Reinstall AXON or run from the development repository.", file=sys.stderr)
        return 1
    try:
        return subprocess.call(
            [str(node), "server.js"],
            cwd=str(app_dir),
            env=_server_env(port),
        )
    except OSError as exc:
        print(f"AXON: could not start Zenith panel — {exc}", file=sys.stderr)
        return 1


def run_zenith_dev(port: int = DEFAULT_ZENITH_PORT) -> int:
    web_dir = dev_zenith_dir()
    if not web_dir:
        print("AXON: zenith-web not found.", file=sys.stderr)
        return 1
    try:
        return subprocess.call(
            ["npm", "run", "dev", "--", "-p", str(port)],
            cwd=str(web_dir),
            shell=sys.platform == "win32",
        )
    except OSError as exc:
        print(f"AXON: could not start web server — {exc}", file=sys.stderr)
        return 1
