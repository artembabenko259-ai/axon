"""Observe mode — model-initiated screen capture + vision.

The agent calls ``take_screenshot`` when it decides visual verification is needed.
No automatic captures after shell or other tools.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_policy import load_runtime_policy
from ui.session_timeline import session_timeline
from ui.vision_models import (
    SUGGESTED_VISION_MODELS,
    is_confirmed_non_vision,
    vision_required_message,
)

_observe_llm: Any = None

_SCREENSHOT_SAVED_RE = re.compile(
    r"Screenshot saved:\s*(?P<path>.+?)\s*$",
    re.MULTILINE,
)


def set_observe_llm(llm: Any) -> None:
    """Register active LLMManager (called from LLMManager.__init__)."""
    global _observe_llm
    _observe_llm = llm


def observe_dir() -> Path:
    root = Path.cwd() / ".axon" / "observe"
    root.mkdir(parents=True, exist_ok=True)
    return root


def capture_screenshot(filename: str | None = None) -> Path:
    """Save full-screen screenshot; requires Pillow on Windows."""
    try:
        from PIL import ImageGrab
    except ImportError as exc:
        raise RuntimeError("Pillow is required for screenshots on Windows.") from exc

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    name = filename or f"screen-{stamp}.png"
    path = observe_dir() / name
    ImageGrab.grab().save(path, format="PNG")
    return path


def observe_enabled() -> bool:
    """When false, take_screenshot tool is hidden and denied."""
    return load_runtime_policy().observe_mode_enabled


def _resolve_screenshot_path(tool_result: str) -> Path | None:
    match = _SCREENSHOT_SAVED_RE.search(tool_result.strip())
    if not match:
        return None
    raw = match.group("path").strip().strip("\"'")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    else:
        path = path.resolve()
    return path if path.is_file() else None


def take_screenshot_tool(path: str = "") -> str:
    """Native tool handler — save screenshot to workspace."""
    target = path.strip() or f"screenshot-{datetime.now().strftime('%H%M%S')}.png"
    if not target.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        target += ".png"
    out = capture_screenshot(Path(target).name)
    rel = out.name
    try:
        rel = str(out.relative_to(Path.cwd()))
    except ValueError:
        rel = str(out)
    session_timeline.record_observe(rel, "take_screenshot")
    return f"Screenshot saved: {rel}"


async def enrich_screenshot_result(tool_result: str, *, purpose: str = "") -> str:
    """After take_screenshot: load into vision context or return text analysis."""
    path = _resolve_screenshot_path(tool_result)
    if path is None:
        return tool_result

    llm = _observe_llm
    if llm is None:
        return (
            f"{tool_result}\n\n"
            "(Vision bridge unavailable — use /image with a vision model to view the screen.)"
        )

    goal = purpose.strip() or "Verify what is on screen and whether the task outcome looks correct."
    vision_prompt = (
        f"[take_screenshot] {goal}\n"
        "Describe: active window, key UI elements, visible text/errors, "
        "and whether the expected result appears to have succeeded."
    )

    model = str(getattr(llm, "model", ""))
    text_only = is_confirmed_non_vision(model)

    if not text_only:
        loader = getattr(llm, "load_image_into_context", None)
        if callable(loader):
            err = loader(str(path), vision_prompt)
            if not err:
                return (
                    f"{tool_result}\n\n"
                    "The screenshot is now in your context — analyze what you see and continue."
                )
            return f"{tool_result}\n\n{err}"

    if text_only:
        hint = SUGGESTED_VISION_MODELS[0]
        note = vision_required_message(model)
        analyzer = getattr(llm, "analyze_image_once_async", None)
        if callable(analyzer):
            try:
                summary = await analyzer(str(path), vision_prompt)
                if summary.strip():
                    session_timeline.record_observe(
                        str(path.name),
                        summary[:120],
                    )
                    return f"{tool_result}\n\nScreen analysis:\n{summary.strip()}"
            except Exception as exc:
                return (
                    f"{tool_result}\n\n"
                    f"{note}\n"
                    f"Vision analysis failed: {exc}. Try /model {hint}"
                )
        return f"{tool_result}\n\n{note}"

    return tool_result
