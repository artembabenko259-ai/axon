"""Windows system tray for AXON background serve."""

from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

TRAY_AVAILABLE = False

try:
    import pystray
    from PIL import Image, ImageDraw

    TRAY_AVAILABLE = True
except ImportError:
    pystray = None  # type: ignore[assignment,misc]
    Image = None  # type: ignore[assignment,misc]
    ImageDraw = None  # type: ignore[assignment,misc]


def _default_icon(size: int = 64):
    image = Image.new("RGBA", (size, size), (10, 10, 10, 255))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, size - 8, size - 8), outline=(103, 232, 249, 255), width=3)
    return image


def _load_icon() -> object:
    candidates = [
        Path(__file__).resolve().parent / "assets" / "icon.ico",
        Path(__file__).resolve().parent / "vscode-extension" / "media" / "icon.svg",
    ]
    for path in candidates:
        if path.is_file() and Image is not None:
            try:
                return Image.open(path)
            except Exception:
                continue
    return _default_icon()


def run_tray(
    *,
    on_quit: callable | None = None,
    panel_url: str = "http://127.0.0.1:3000",
) -> None:
    if not TRAY_AVAILABLE:
        print(
            "AXON: tray requires pystray and Pillow. "
            "Install: pip install pystray Pillow",
            file=sys.stderr,
        )
        return

    stop_event = threading.Event()

    def _open_panel(_icon, _item) -> None:
        webbrowser.open(panel_url)

    def _quit(_icon, _item) -> None:
        stop_event.set()
        if on_quit:
            on_quit()
        _icon.stop()

    icon = pystray.Icon(
        "axon",
        _load_icon(),
        "AXON",
        menu=pystray.Menu(
            pystray.MenuItem("Open Zenith", _open_panel, default=True),
            pystray.MenuItem("Quit", _quit),
        ),
    )

    thread = threading.Thread(target=icon.run, daemon=True)
    thread.start()
    stop_event.wait()


def run_tray_blocking(**kwargs) -> None:
    """Block until user quits from tray menu."""
    if not TRAY_AVAILABLE:
        run_tray(**kwargs)
        return

    def _noop():
        pass

    icon = pystray.Icon(
        "axon",
        _load_icon(),
        "AXON",
        menu=pystray.Menu(
            pystray.MenuItem(
                "Open Zenith",
                lambda _i, _it: webbrowser.open(kwargs.get("panel_url", "http://127.0.0.1:3000")),
                default=True,
            ),
            pystray.MenuItem("Quit", lambda i, _it: i.stop()),
        ),
    )
    icon.run()
