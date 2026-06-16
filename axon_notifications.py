"""Desktop notification sounds for AXON (approval needed, task done)."""

from __future__ import annotations

import sys
import threading
from dataclasses import dataclass
from pathlib import Path

from runtime_policy import load_runtime_policy


@dataclass
class NotificationSettings:
    enabled: bool = True
    sound_on_approval: bool = True
    sound_on_complete: bool = True
    volume: float = 1.0


def load_notification_settings() -> NotificationSettings:
    policy = load_runtime_policy()
    return NotificationSettings(
        enabled=bool(getattr(policy, "notifications_enabled", True)),
        sound_on_approval=bool(getattr(policy, "sound_on_approval", True)),
        sound_on_complete=bool(getattr(policy, "sound_on_complete", True)),
        volume=float(getattr(policy, "notification_volume", 1.0)),
    )


def _beep_windows(frequency: int, duration_ms: int) -> None:
    try:
        import winsound

        winsound.Beep(frequency, duration_ms)
    except Exception:
        sys.stdout.write("\a")
        sys.stdout.flush()


def _play_tone(frequency: int, duration_ms: int, *, volume: float) -> None:
    if volume <= 0:
        return
    if sys.platform == "win32":
        _beep_windows(frequency, duration_ms)
        return
    sys.stdout.write("\a")
    sys.stdout.flush()


def _play_async(fn) -> None:
    threading.Thread(target=fn, daemon=True).start()


def notify_approval_needed() -> None:
    settings = load_notification_settings()
    if not settings.enabled or not settings.sound_on_approval:
        return

    def _run() -> None:
        _play_tone(880, 120, volume=settings.volume)
        _play_tone(660, 120, volume=settings.volume)

    _play_async(_run)


def notify_agent_complete() -> None:
    settings = load_notification_settings()
    if not settings.enabled or not settings.sound_on_complete:
        return

    def _run() -> None:
        _play_tone(523, 90, volume=settings.volume)
        _play_tone(784, 140, volume=settings.volume)

    _play_async(_run)


def bundled_sound(name: str) -> Path | None:
    from axon_runtime import install_root

    candidate = install_root() / "assets" / "sounds" / name
    return candidate if candidate.is_file() else None
