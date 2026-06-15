"""AXON account login via runaxon.xyz (device authorization flow)."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from axon_runtime import user_data_dir

DEFAULT_AUTH_BASE = "https://runaxon.xyz/api/auth"
AUTH_PATH = user_data_dir() / "auth.json"
POLL_INTERVAL_SEC = 2.0
POLL_TIMEOUT_SEC = 600.0


@dataclass(frozen=True)
class AuthSession:
    token: str
    email: str
    expires_at: int

    @property
    def is_valid(self) -> bool:
        return bool(self.token) and self.expires_at > int(time.time())


def auth_api_base() -> str:
    return (os.environ.get("AXON_AUTH_URL") or DEFAULT_AUTH_BASE).rstrip("/")


def load_session() -> AuthSession | None:
    if not AUTH_PATH.is_file():
        return None
    try:
        raw = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
        session = AuthSession(
            token=str(raw.get("token", "")).strip(),
            email=str(raw.get("email", "")).strip(),
            expires_at=int(raw.get("expires_at", 0)),
        )
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None
    return session if session.is_valid else None


def save_session(session: AuthSession) -> None:
    AUTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUTH_PATH.write_text(
        json.dumps(
            {
                "token": session.token,
                "email": session.email,
                "expires_at": session.expires_at,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def clear_session() -> None:
    if AUTH_PATH.is_file():
        try:
            AUTH_PATH.unlink()
        except OSError:
            pass


def _request_json(
    method: str,
    url: str,
    payload: dict | None = None,
    *,
    timeout: float = 20.0,
) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(detail)
            message = parsed.get("error") or detail
        except json.JSONDecodeError:
            message = detail or str(exc)
        raise RuntimeError(message) from exc
    except OSError as exc:
        raise RuntimeError(f"Could not reach {url}") from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Invalid response from auth server") from exc


def start_device_session() -> dict:
    base = auth_api_base()
    data = _request_json("POST", f"{base}/device-start.php")
    if not data.get("ok"):
        raise RuntimeError(data.get("error") or "Failed to start device session")
    return data


def poll_device_session(device_id: str) -> dict:
    base = auth_api_base()
    url = f"{base}/device-poll.php?device_id={urllib.request.quote(device_id)}"
    return _request_json("GET", url)


def run_login_flow(*, open_browser: bool = True) -> AuthSession:
    existing = load_session()
    if existing:
        return existing

    device = start_device_session()
    device_id = str(device["device_id"])
    verify_url = str(device.get("verify_url") or "")
    user_code = str(device.get("user_code") or "")

    if open_browser and verify_url:
        webbrowser.open(verify_url)

    print("AXON Login")
    print(f"  1. Browser should open: {verify_url or 'https://runaxon.xyz/login.html'}")
    if user_code:
        print(f"  2. Pairing code: {user_code}")
    print("  3. Register or sign in with your email")
    print("  4. Waiting for authorization…")

    deadline = time.time() + POLL_TIMEOUT_SEC
    while time.time() < deadline:
        result = poll_device_session(device_id)
        status = str(result.get("status", ""))
        if status == "approved":
            token = str(result.get("token", "")).strip()
            email = str(result.get("email", "")).strip()
            expires_at = int(result.get("expires_at", 0))
            if not token:
                raise RuntimeError("Auth server returned empty token")
            session = AuthSession(token=token, email=email, expires_at=expires_at)
            save_session(session)
            return session
        if status == "expired":
            raise RuntimeError("Login timed out — run /login again")
        time.sleep(POLL_INTERVAL_SEC)

    raise RuntimeError("Login timed out — complete sign-in in the browser, then run /login again")


def session_summary() -> str:
    session = load_session()
    if not session:
        return "Not signed in"
    return f"Signed in as {session.email}"


def logout() -> None:
    clear_session()
