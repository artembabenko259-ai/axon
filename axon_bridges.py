"""Modular Chat Bridges for AXON CLI — Telegram, Discord, and Slack integration."""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable

from runtime_policy import load_runtime_policy, save_runtime_policy
from llm_client import LLMManager


# ============================================================================
#  Shared Prompt Executor
# ============================================================================

async def run_bridge_prompt(
    prompt: str,
    send_reply_fn: Callable[[str], None],
    platform_name: str
) -> None:
    policy = load_runtime_policy()
    
    status_msg = f"🤖 *AXON ({platform_name}):* Processing request..."
    if not policy.autopilot_enabled and not policy.autonomy_enabled:
        status_msg += "\n_(Note: Autopilot is OFF. Destructive tools will be auto-denied. Use /autopilot on for autonomy.)_"
    
    try:
        send_reply_fn(status_msg)
    except Exception:
        pass
    
    workspace = Path.cwd()
    llm = LLMManager(workspace=workspace)
    
    from autopilot_mode import is_autopilot_active
    from skills.tools import ApprovalDecision
    
    async def approve(tool: str, detail: str) -> ApprovalDecision:
        if is_autopilot_active() or policy.autonomy_enabled:
            return "once"
        return "deny"
        
    llm.set_approval_callback(approve)
    
    try:
        result = await llm.send_message_async(prompt)
        if result.ok and result.content:
            send_reply_fn(f"✅ *AXON Response:*\n\n{result.content}")
        else:
            send_reply_fn(f"❌ *AXON Error:*\n{result.display_text}")
    except Exception as exc:
        send_reply_fn(f"❌ *AXON Exec Error:* {exc}")


def _dispatch_prompt(prompt: str, send_reply_fn: Callable[[str], None], platform_name: str) -> None:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    if loop.is_running():
        asyncio.run_coroutine_threadsafe(
            run_bridge_prompt(prompt, send_reply_fn, platform_name),
            loop
        )
    else:
        loop.run_until_complete(run_bridge_prompt(prompt, send_reply_fn, platform_name))


# ============================================================================
#  Telegram Adapter
# ============================================================================

def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception:
        # Fallback to plain text
        try:
            payload.pop("parse_mode", None)
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as exc:
            print(f"[telegram error] {exc}")


def _telegram_loop() -> None:
    print("[bridges] Telegram bot listener active.")
    last_update_id = None
    
    while True:
        try:
            policy = load_runtime_policy()
            token = (policy.telegram_bot_token or "").strip()
            chat_id = (policy.telegram_chat_id or "").strip()
            
            if not token:
                time.sleep(5.0)
                continue
                
            url = f"https://api.telegram.org/bot{token}/getUpdates"
            if last_update_id is not None:
                url += f"?offset={last_update_id}&timeout=5"
            else:
                url += "?timeout=2"
                
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                updates = res.get("result", []) if res.get("ok") else []
                
            for update in updates:
                update_id = update.get("update_id")
                if update_id is not None:
                    last_update_id = update_id + 1
                    
                message = update.get("message")
                if not message or "text" not in message:
                    continue
                    
                msg_chat_id = str(message["chat"]["id"])
                text = message["text"].strip()
                
                if not chat_id:
                    pin = (policy.bridge_pin or "").strip()
                    if text == pin:
                        policy.telegram_chat_id = msg_chat_id
                        save_runtime_policy(policy)
                        chat_id = msg_chat_id
                        send_telegram_message(
                            token,
                            chat_id,
                            "🎉 *AXON:* Telegram bot paired successfully!\nYou now have remote control over this AXON session."
                        )
                    else:
                        send_telegram_message(
                            token,
                            msg_chat_id,
                            "🔑 *AXON Pairing Required*\nPlease send the 6-digit security PIN shown in your PC terminal to pair this chat and authorize commands."
                        )
                    continue

                if msg_chat_id != chat_id:
                    send_telegram_message(token, msg_chat_id, "⚠️ Unauthorized access.")
                    continue
                    
                if text.lower() == "/status":
                    from autopilot_mode import is_autopilot_active
                    status = "ON" if is_autopilot_active() else "OFF"
                    send_telegram_message(
                        token,
                        chat_id,
                        f"🤖 *AXON Status*\nWorkspace: `{Path.cwd().resolve()}`\nAutopilot: `{status}`"
                    )
                    continue
                    
                _dispatch_prompt(
                    text,
                    lambda reply: send_telegram_message(token, chat_id, reply),
                    "Telegram"
                )
        except Exception as exc:
            print(f"[telegram error] {exc}")
        time.sleep(1.0)


# ============================================================================
#  Discord Adapter (Using HTTP Poll + Webhook/SendMessage)
# ============================================================================

def send_discord_message(token: str, channel_id: str, text: str) -> None:
    if not token or not channel_id:
        return
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    payload = {"content": text}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bot {token}",
                "Content-Type": "application/json",
                "User-Agent": "AXON-Discord-Bridge/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as exc:
        print(f"[discord error] Failed to send: {exc}")


def _discord_loop() -> None:
    print("[bridges] Discord bot listener active.")
    last_message_id = None
    
    # Pre-populate last message ID to avoid executing historic messages on start
    try:
        policy = load_runtime_policy()
        token = (policy.discord_bot_token or "").strip()
        channel_id = (policy.discord_channel_id or "").strip()
        if token and channel_id:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=1"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bot {token}", "User-Agent": "AXON-Discord-Bridge/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                messages = json.loads(resp.read().decode("utf-8"))
                if messages:
                    last_message_id = messages[0]["id"]
    except Exception:
        pass

    while True:
        try:
            policy = load_runtime_policy()
            token = (policy.discord_bot_token or "").strip()
            channel_id = (policy.discord_channel_id or "").strip()
            
            if not token or not channel_id:
                time.sleep(5.0)
                continue
                
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=5"
            if last_message_id:
                url += f"&after={last_message_id}"
                
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bot {token}", "User-Agent": "AXON-Discord-Bridge/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                messages = json.loads(resp.read().decode("utf-8"))
                
            # Messages returned are newest first, so sort chronologically
            for msg in sorted(messages, key=lambda m: m["id"]):
                last_message_id = msg["id"]
                
                # Skip bot's own messages
                author = msg.get("author", {})
                if author.get("bot"):
                    continue
                    
                content = msg.get("content", "").strip()
                if not content:
                    continue
                    
                if content.lower() == "!status":
                    from autopilot_mode import is_autopilot_active
                    status = "ON" if is_autopilot_active() else "OFF"
                    send_discord_message(
                        token,
                        channel_id,
                        f"🤖 **AXON Status**\nWorkspace: `{Path.cwd().resolve()}`\nAutopilot: `{status}`"
                    )
                    continue
                    
                _dispatch_prompt(
                    content,
                    lambda reply: send_discord_message(token, channel_id, reply),
                    "Discord"
                )
        except Exception as exc:
            print(f"[discord loop error] {exc}")
        time.sleep(2.0)


# ============================================================================
#  Slack Adapter (Using HTTP Poll + PostMessage)
# ============================================================================

def send_slack_message(token: str, channel_id: str, text: str) -> None:
    if not token or not channel_id:
        return
    url = "https://slack.com/api/chat.postMessage"
    payload = {"channel": channel_id, "text": text}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "AXON-Slack-Bridge/1.0"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except Exception as exc:
        print(f"[slack error] Failed to send: {exc}")


def _slack_loop() -> None:
    print("[bridges] Slack bot listener active.")
    last_timestamp = str(time.time())
    
    while True:
        try:
            policy = load_runtime_policy()
            token = (policy.slack_bot_token or "").strip()
            channel_id = (policy.slack_channel_id or "").strip()
            
            if not token or not channel_id:
                time.sleep(5.0)
                continue
                
            url = f"https://slack.com/api/conversations.history?channel={channel_id}&oldest={last_timestamp}&limit=10"
            req = urllib.request.Request(
                url,
                headers={"Authorization": f"Bearer {token}", "User-Agent": "AXON-Slack-Bridge/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                
            if res.get("ok"):
                messages = res.get("messages", [])
                # Sort oldest first
                for msg in sorted(messages, key=lambda m: float(m.get("ts", 0))):
                    last_timestamp = msg.get("ts")
                    
                    # Ignore bot messages
                    if "bot_id" in msg or msg.get("subtype") == "bot_message":
                        continue
                        
                    content = msg.get("text", "").strip()
                    if not content:
                        continue
                        
                    if content.lower() == "!status":
                        from autopilot_mode import is_autopilot_active
                        status = "ON" if is_autopilot_active() else "OFF"
                        send_slack_message(
                            token,
                            channel_id,
                            f"🤖 *AXON Status*\nWorkspace: `{Path.cwd().resolve()}`\nAutopilot: `{status}`"
                        )
                        continue
                        
                    _dispatch_prompt(
                        content,
                        lambda reply: send_slack_message(token, channel_id, reply),
                        "Slack"
                    )
        except Exception as exc:
            print(f"[slack loop error] {exc}")
        time.sleep(2.0)


# ============================================================================
#  Startup Manager
# ============================================================================

def start_all_bridges() -> None:
    """Start Telegram, Discord, and Slack listener threads in background."""
    # Telegram bot
    t_tg = threading.Thread(target=_telegram_loop, name="AxonTelegramBridge", daemon=True)
    t_tg.start()
    
    # Discord bot
    t_ds = threading.Thread(target=_discord_loop, name="AxonDiscordBridge", daemon=True)
    t_ds.start()
    
    # Slack bot
    t_sl = threading.Thread(target=_slack_loop, name="AxonSlackBridge", daemon=True)
    t_sl.start()
