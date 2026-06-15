from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axon_runtime import user_data_dir

SESSIONS_DIR = user_data_dir() / "sessions"


@dataclass
class SessionMeta:
    id: str
    title: str
    model: str
    updated_at: str
    message_count: int
    tokens: int = 0


@dataclass
class SessionData:
    meta: SessionMeta
    messages: list[dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _session_path(session_id: str) -> Path:
    return SESSIONS_DIR / f"{session_id}.json"


def ensure_sessions_dir() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def list_sessions() -> list[SessionMeta]:
    ensure_sessions_dir()
    metas: list[SessionMeta] = []
    for path in sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            meta = raw.get("meta") or {}
            metas.append(
                SessionMeta(
                    id=str(meta.get("id", path.stem)),
                    title=str(meta.get("title", "Untitled")),
                    model=str(meta.get("model", "")),
                    updated_at=str(meta.get("updated_at", "")),
                    message_count=int(meta.get("message_count", 0)),
                    tokens=int(meta.get("tokens", 0)),
                )
            )
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
    return metas


def save_session(
    *,
    session_id: str | None,
    messages: list[dict[str, Any]],
    model: str,
    tokens: int = 0,
    title: str | None = None,
) -> SessionMeta:
    ensure_sessions_dir()
    sid = session_id or uuid.uuid4().hex[:12]
    first_user = next(
        (m.get("content", "") for m in messages if m.get("role") == "user"),
        "",
    )
    if isinstance(first_user, list):
        first_user = "vision message"
    session_title = (title or str(first_user)[:80] or "Untitled").strip()
    meta = SessionMeta(
        id=sid,
        title=session_title,
        model=model,
        updated_at=_now_iso(),
        message_count=len(messages),
        tokens=tokens,
    )
    payload = {"meta": asdict(meta), "messages": messages}
    _session_path(sid).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def load_session(session_id: str) -> SessionData | None:
    path = _session_path(session_id.strip())
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta_raw = raw.get("meta") or {}
        meta = SessionMeta(
            id=str(meta_raw.get("id", session_id)),
            title=str(meta_raw.get("title", "Untitled")),
            model=str(meta_raw.get("model", "")),
            updated_at=str(meta_raw.get("updated_at", "")),
            message_count=int(meta_raw.get("message_count", 0)),
            tokens=int(meta_raw.get("tokens", 0)),
        )
        messages = raw.get("messages") or []
        if not isinstance(messages, list):
            messages = []
        return SessionData(meta=meta, messages=messages)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id.strip())
    if not path.is_file():
        return False
    path.unlink()
    return True
