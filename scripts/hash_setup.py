#!/usr/bin/env python3
"""Print SHA-256 for the Inno Setup release and optionally patch winget manifests."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SETUP = ROOT / "release" / "AXON_Setup_v1.0.0.exe"
FALLBACK_SETUP = ROOT / "dist" / "setup" / "AXON_Setup_v1.0.0.exe"
WINGET_INSTALLER = ROOT / "winget" / "Core.AXON.installer.yaml"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def patch_manifest(sha256: str) -> None:
    text = WINGET_INSTALLER.read_text(encoding="utf-8")
    updated = re.sub(
        r"(InstallerSha256:\s*)(?:PLACEHOLDER_HASH|[A-Fa-f0-9]{64})",
        rf"\g<1>{sha256}",
        text,
        count=1,
    )
    WINGET_INSTALLER.write_text(updated, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Hash AXON_Setup release executable.")
    parser.add_argument(
        "--setup",
        type=Path,
        default=DEFAULT_SETUP,
        help="Path to AXON_Setup_v1.0.0.exe",
    )
    parser.add_argument(
        "--patch-manifest",
        action="store_true",
        help="Write hash into winget/Core.AXON.installer.yaml",
    )
    args = parser.parse_args()

    setup_path = args.setup if args.setup.is_absolute() else ROOT / args.setup
    if not setup_path.is_file() and FALLBACK_SETUP.is_file():
        setup_path = FALLBACK_SETUP
    if not setup_path.is_file():
        print(f"Setup executable not found: {setup_path}", file=sys.stderr)
        print("Run: iscc scripts\\installer.iss", file=sys.stderr)
        return 1

    digest = sha256_file(setup_path)
    if args.patch_manifest:
        patch_manifest(digest)

    print(f"File    : {setup_path.relative_to(ROOT)}")
    print(f"SHA-256 : {digest}")
    print(f"Paste into: winget/Core.AXON.installer.yaml -> InstallerSha256")
    return 0


if __name__ == "__main__":
    sys.exit(main())
