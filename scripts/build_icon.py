#!/usr/bin/env python3
"""Build assets/axon.ico from assets/axon-icon-source.png (multi-size Windows icon)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "axon-icon-source.png"
ICO_OUT = ROOT / "assets" / "axon.ico"
PNG_OUT = ROOT / "assets" / "axon-icon-512.png"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main() -> int:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Install Pillow: pip install Pillow") from exc

    if not SOURCE.is_file():
        raise SystemExit(f"Missing source image: {SOURCE}")

    img = Image.open(SOURCE).convert("RGBA")
    master = img.resize((256, 256), Image.Resampling.LANCZOS)
    master.save(
        ICO_OUT,
        format="ICO",
        sizes=[(size, size) for size in SIZES],
    )
    img.resize((512, 512), Image.Resampling.LANCZOS).save(PNG_OUT)

    print(f"ICO : {ICO_OUT.relative_to(ROOT)} ({ICO_OUT.stat().st_size:,} bytes)")
    print(f"PNG : {PNG_OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
