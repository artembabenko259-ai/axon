from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from axon_runtime import user_data_dir

AUDIT_PATH = user_data_dir() / "audit.log"


def log_tool_event(
    *,
    tool: str,
    detail: str,
    source: str,
    outcome: str,
) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "detail": detail[:500],
        "source": source,
        "outcome": outcome[:200],
    }
    with AUDIT_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def scan_secrets(text: str) -> list[str]:
    patterns = [
        (r"sk-or-v1-[A-Za-z0-9]{20,}", "OpenRouter API key"),
        (r"sk-[A-Za-z0-9]{20,}", "API key pattern"),
        (r"AKIA[0-9A-Z]{16}", "AWS access key"),
        (r"-----BEGIN (RSA |OPENSSH )?PRIVATE KEY-----", "Private key"),
    ]
    import re

    hits: list[str] = []
    for pattern, label in patterns:
        if re.search(pattern, text):
            hits.append(label)
    return hits
