"""Watch a folder and trigger AXON when files change."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

from axon_runtime import install_root

DEFAULT_PROMPT = (
    "Files changed in the watched project. Review recent changes and suggest "
    "or apply safe improvements. Summarize what you did."
)


def _dir_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(path.rglob("*")):
        if not file.is_file():
            continue
        if any(part.startswith(".") for part in file.parts):
            continue
        if file.suffix.lower() in {".pyc", ".exe", ".dll", ".png", ".jpg", ".webp"}:
            continue
        try:
            stat = file.stat()
        except OSError:
            continue
        digest.update(f"{file}:{stat.st_mtime_ns}:{stat.st_size}".encode())
    return digest.hexdigest()


def _run_prompt(prompt: str, cwd: Path) -> int:
    exe = install_root() / "axon.exe"
    if exe.is_file():
        cmd = [str(exe), "-p", prompt, "--cwd", str(cwd)]
    else:
        cmd = [sys.executable, str(install_root() / "cli.py"), "-p", prompt, "--cwd", str(cwd)]
    return subprocess.call(cmd)


def run_watch(
    target: Path,
    *,
    interval: float = 5.0,
    prompt: str | None = None,
    once: bool = False,
) -> int:
    root = target.resolve()
    if not root.is_dir():
        print(f"AXON: not a directory — {root}", file=sys.stderr)
        return 1

    effective_prompt = (prompt or "").strip() or DEFAULT_PROMPT
    print(f"AXON watch — {root} (every {interval}s, Ctrl+C to stop)")
    last = _dir_fingerprint(root)
    try:
        while True:
            time.sleep(interval)
            current = _dir_fingerprint(root)
            if current == last:
                continue
            last = current
            print("[watch] change detected — running AXON…")
            code = _run_prompt(effective_prompt, root)
            if once:
                return code
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0
