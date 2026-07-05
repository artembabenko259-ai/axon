"""Desktop popup and sounds notifications for AXON (approval needed, task done) with chat bridge broadcasts."""

from __future__ import annotations

import sys
import subprocess
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


def send_desktop_notification(title: str, message: str) -> None:
    settings = load_notification_settings()
    if not settings.enabled:
        return

    def _run() -> None:
        try:
            if sys.platform == "win32":
                escaped_msg = message.replace("'", "''").replace("\n", " ")
                escaped_title = title.replace("'", "''")
                ps_script = (
                    "[void] [System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms'); "
                    "$objNotification = New-Object System.Windows.Forms.NotifyIcon; "
                    "$objNotification.Icon = [System.Drawing.SystemIcons]::Information; "
                    f"$objNotification.BalloonTipIcon = 'Info'; "
                    f"$objNotification.BalloonTipText = '{escaped_msg}'; "
                    f"$objNotification.BalloonTipTitle = '{escaped_title}'; "
                    "$objNotification.Visible = $True; "
                    "$objNotification.ShowBalloonTip(5000);"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_script],
                    capture_output=True,
                    creationflags=0x08000000  # CREATE_NO_WINDOW
                )
            elif sys.platform == "darwin":
                escaped_msg = message.replace('"', '\\"')
                escaped_title = title.replace('"', '\\"')
                applescript = f'display notification "{escaped_msg}" with title "{escaped_title}"'
                subprocess.run(["osascript", "-e", applescript], capture_output=True)
            else:
                # Linux (notify-send)
                subprocess.run(["notify-send", title, message], capture_output=True)
        except Exception as exc:
            sys.stderr.write(f"[notification error] {exc}\n")

    _play_async(_run)


def send_bridge_notifications(message: str) -> None:
    try:
        policy = load_runtime_policy()
        # Telegram
        tg_token = (policy.telegram_bot_token or "").strip()
        tg_chat = (policy.telegram_chat_id or "").strip()
        if tg_token and tg_chat:
            from axon_bridges import send_telegram_message
            send_telegram_message(tg_token, tg_chat, message)

        # Discord
        ds_token = (policy.discord_bot_token or "").strip()
        ds_chan = (policy.discord_channel_id or "").strip()
        if ds_token and ds_chan:
            from axon_bridges import send_discord_message
            send_discord_message(ds_token, ds_chan, message)

        # Slack
        sl_token = (policy.slack_bot_token or "").strip()
        sl_chan = (policy.slack_channel_id or "").strip()
        if sl_token and sl_chan:
            from axon_bridges import send_slack_message
            send_slack_message(sl_token, sl_chan, message)
    except Exception as exc:
        sys.stderr.write(f"[bridge notification error] {exc}\n")


def notify_approval_needed(tool_name: str = "", detail: str = "") -> None:
    settings = load_notification_settings()
    if not settings.enabled:
        return

    if settings.sound_on_approval:
        def _run_sound() -> None:
            _play_tone(880, 120, volume=settings.volume)
            _play_tone(660, 120, volume=settings.volume)
        _play_async(_run_sound)

    msg = f"Tool '{tool_name}' requires your approval." if tool_name else "Action requires your approval."
    if detail:
        msg += f" Details: {detail}"
    if len(msg) > 120:
        msg = msg[:117] + "..."
    send_desktop_notification("AXON - Approval Required", msg)

    # Bridge alert
    bridge_msg = f"⚠️ *AXON: Approval Required*\nTool: `{tool_name or 'Unknown'}`\nDetails: {detail or 'None'}"
    send_bridge_notifications(bridge_msg)


def notify_agent_complete(status: str = "success", message: str = "") -> None:
    settings = load_notification_settings()
    if not settings.enabled:
        return

    if settings.sound_on_complete:
        def _run_sound() -> None:
            _play_tone(523, 90, volume=settings.volume)
            _play_tone(784, 140, volume=settings.volume)
        _play_async(_run_sound)

    title = "AXON - Task Completed"
    msg = message or "The agent has finished the requested task."
    if status == "error":
        title = "AXON - Task Failed"
        msg = message or "The agent encountered an error."

    if len(msg) > 120:
        msg = msg[:117] + "..."
    send_desktop_notification(title, msg)

    icon = "✅" if status != "error" else "❌"
    bridge_msg = f"{icon} *AXON Notification:*\n{msg}"
    send_bridge_notifications(bridge_msg)


def bundled_sound(name: str) -> Path | None:
    from axon_runtime import install_root
    candidate = install_root() / "assets" / "sounds" / name
    return candidate if candidate.is_file() else None
