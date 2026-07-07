"""AXON Dev-mode logging — activated by AXON_DEV=1 environment variable.

Usage:
    axon shard --dev        # sets AXON_DEV=1 before spawning daemon
    axon repl --dev         # same for the REPL backend

All Python modules that call `get_logger(__name__)` will automatically
write structured records to the rotating dev log file when AXON_DEV=1.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

_INITIALIZED = False
_LOG_PATH: Path | None = None

# ── public API ───────────────────────────────────────────────────────────────

def is_dev_mode() -> bool:
    return os.environ.get("AXON_DEV", "").strip() == "1"


def log_path() -> Path | None:
    return _LOG_PATH


def setup(*, force: bool = False) -> Path | None:
    """Configure root logger for dev mode.  Call once at startup.

    Returns the log file path, or None when dev mode is inactive.
    """
    global _INITIALIZED, _LOG_PATH

    if _INITIALIZED and not force:
        return _LOG_PATH

    if not is_dev_mode():
        _INITIALIZED = True
        return None

    # ── resolve log directory ──────────────────────────────────────────────
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    log_dir = base / "AXON" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pid   = os.getpid()
    log_file = log_dir / f"dev_{stamp}_{pid}.log"

    # ── configure root logger ──────────────────────────────────────────────
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d  %(levelname)-8s  %(name)-30s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Rotating file handler — max 20 MB, keep 3 backups
    fh = RotatingFileHandler(
        log_file,
        maxBytes=20 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler — INFO+ so the terminal isn't flooded
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Silence noisy third-party loggers
    for noisy in ("websockets", "asyncio", "urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _LOG_PATH = log_file
    _INITIALIZED = True

    logging.info("AXON DEV MODE — logging to %s", log_file)
    return log_file


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger.  Works regardless of dev mode."""
    return logging.getLogger(name)
