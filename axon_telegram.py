"""Telegram Bot integration for AXON CLI — write to AXON from anywhere."""

from __future__ import annotations

import asyncio
import json
import threading
import time
import urllib.request
from pathlib import Path

from runtime_policy import load_runtime_policy, save_runtime_policy
from llm_client import LLMManager


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # 1. Try sending with Markdown
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return
    except Exception:
        # 2. Fallback to plain text
        payload = {"chat_id": chat_id, "text": text}
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                return
        except Exception as exc:
            print(f"[telegram error] Failed to send message: {exc}")


def get_telegram_updates(token: str, offset: int | None = None) -> list[dict]:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    if offset is not None:
        url += f"?offset={offset}&timeout=5"
    else:
        url += "?timeout=2"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode("utf-8"))
            if res.get("ok"):
                return res.get("result", [])
    except Exception as exc:
        # Silently fail to avoid console flooding when internet is offline
        pass
    return []


async def _run_prompt_async(prompt: str, token: str, chat_id: str) -> None:
    policy = load_runtime_policy()
    
    # Notify user that AXON is working
    status_msg = "🤖 *AXON:* Processing your request..."
    if not policy.autopilot_enabled and not policy.autonomy_enabled:
        status_msg += "\n_(Note: Autopilot mode is OFF. Dangerous tools like shell commands might be denied. Set autopilot or autonomy ON for full independence.)_"
    
    send_telegram_message(token, chat_id, status_msg)
    
    # Build LLM manager
    workspace = Path.cwd()
    llm = LLMManager(workspace=workspace)
    
    # Autopilot approval handler: auto-approves if autonomy or autopilot is active
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
            send_telegram_message(token, chat_id, f"✅ *AXON Response:*\n\n{result.content}")
        else:
            send_telegram_message(token, chat_id, f"❌ *AXON Error:*\n{result.display_text}")
    except Exception as exc:
        send_telegram_message(token, chat_id, f"❌ *AXON Exec Error:* {exc}")


def _telegram_loop() -> None:
    print("[telegram] Background bot thread started.")
    last_update_id: int | None = None
    
    while True:
        policy = load_runtime_policy()
        token = (policy.telegram_bot_token or "").strip()
        chat_id = (policy.telegram_chat_id or "").strip()
        
        if not token:
            # Sleep and check again later if token gets inserted
            time.sleep(5.0)
            continue
            
        updates = get_telegram_updates(token, offset=last_update_id)
        for update in updates:
            update_id = update.get("update_id")
            if update_id is not None:
                last_update_id = update_id + 1
                
            message = update.get("message")
            if not message:
                continue
                
            msg_chat = message.get("chat", {})
            msg_chat_id = str(msg_chat.get("id", ""))
            text = message.get("text", "").strip()
            
            if not text:
                continue
                
            # 1. Pairing flow
            if not chat_id:
                # Pair successfully with the first person who messages the bot
                policy.telegram_chat_id = msg_chat_id
                save_runtime_policy(policy)
                chat_id = msg_chat_id
                send_telegram_message(
                    token,
                    chat_id,
                    "🎉 *AXON:* Telegram bot successfully paired with this chat!\n"
                    "You can now send prompts to run AXON commands on your machine."
                )
                continue
                
            # 2. Authorization check
            if msg_chat_id != chat_id:
                send_telegram_message(
                    token,
                    msg_chat_id,
                    "⚠️ *AXON:* Unauthorized access. This bot is paired with another user."
                )
                continue
                
            # 3. Handle commands
            if text.lower() == "/status":
                from autopilot_mode import is_autopilot_active
                status = "ON" if is_autopilot_active() else "OFF"
                send_telegram_message(
                    token,
                    chat_id,
                    f"🤖 *AXON Status*\n"
                    f"Workspace: `{Path.cwd().resolve()}`\n"
                    f"Autopilot: `{status}`\n"
                    f"Autonomy: `{policy.autonomy_enabled}`"
                )
                continue
                
            if text.lower().startswith("/autopilot "):
                arg = text[len("/autopilot "):].strip().lower()
                if arg in {"on", "enable"}:
                    policy.autopilot_enabled = True
                    save_runtime_policy(policy)
                    send_telegram_message(token, chat_id, "🤖 Autopilot mode enabled.")
                elif arg in {"off", "disable"}:
                    policy.autopilot_enabled = False
                    save_runtime_policy(policy)
                    send_telegram_message(token, chat_id, "🤖 Autopilot mode disabled.")
                else:
                    send_telegram_message(token, chat_id, "Usage: `/autopilot on` | `/autopilot off`")
                continue
                
            # Run the prompt asynchronously in the event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    _run_prompt_async(text, token, chat_id),
                    loop
                )
            else:
                loop.run_until_complete(_run_prompt_async(text, token, chat_id))
                
        time.sleep(1.0)


def start_telegram_bot() -> None:
    """Start Telegram bot listener thread."""
    t = threading.Thread(target=_telegram_loop, name="AxonTelegramBot", daemon=True)
    t.start()
