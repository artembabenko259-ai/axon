from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from ui.branding import VERSION

DEFAULT_UPDATE_URL = "https://runaxon.xyz/version.json"


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    download_url: str
    winget_id: str
    notes: str


def _update_url() -> str:
    return (os.environ.get("AXON_UPDATE_URL") or DEFAULT_UPDATE_URL).strip()


def fetch_latest_release(timeout: float = 8.0) -> ReleaseInfo | None:
    url = _update_url()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError):
        return None

    version = str(raw.get("version", "")).strip()
    if not version:
        return None

    return ReleaseInfo(
        version=version,
        download_url=str(raw.get("download_url", "")).strip(),
        winget_id=str(raw.get("winget_id", "Core.AXON")).strip(),
        notes=str(raw.get("notes", "")).strip(),
    )


def compare_versions(current: str, latest: str) -> int:
    """Return -1 if current < latest, 0 if equal, 1 if current > latest."""

    def _parts(value: str) -> list[int]:
        parts: list[int] = []
        for piece in value.strip().split("."):
            try:
                parts.append(int(piece))
            except ValueError:
                break
        return parts or [0]

    cur = _parts(current)
    lat = _parts(latest)
    length = max(len(cur), len(lat))
    cur.extend([0] * (length - len(cur)))
    lat.extend([0] * (length - len(lat)))
    if cur < lat:
        return -1
    if cur > lat:
        return 1
    return 0


def check_for_update() -> tuple[bool, str, ReleaseInfo | None]:
    """Return (update_available, message, release_info)."""
    release = fetch_latest_release()
    if release is None:
        return False, f"Could not reach update feed ({_update_url()})", None

    cmp = compare_versions(VERSION, release.version)
    if cmp < 0:
        msg = f"Update available: v{release.version} (you have v{VERSION})"
        if release.download_url:
            msg += f"\n  Download: {release.download_url}"
        if release.winget_id:
            msg += f"\n  Winget: winget install {release.winget_id}"
        return True, msg, release

    return False, f"AXON v{VERSION} is up to date.", release
