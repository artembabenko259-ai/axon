#!/usr/bin/env python3
"""Stage installer + version metadata into deploy/site/ and rebuild runaxon-site.zip."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "deploy" / "site"
DOWNLOADS = SITE / "downloads"
ARCHIVE = DOWNLOADS / "archive"
ZIP_OUT = ROOT / "deploy" / "runaxon-site.zip"


def parse_version() -> str:
    branding = ROOT / "ui" / "branding.py"
    match = re.search(
        r'VERSION\s*=\s*["\']([^"\']+)["\']',
        branding.read_text(encoding="utf-8"),
    )
    return match.group(1) if match else "1.0.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def find_setup(version: str) -> Path:
    for candidate in (
        ROOT / "release" / f"AXON_Setup_v{version}.exe",
        ROOT / "dist" / "setup" / f"AXON_Setup_v{version}.exe",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Installer not found for v{version}. Run build.bat first."
    )


def stage_installer(setup: Path, version: str) -> tuple[Path, Path]:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    versioned_name = f"AXON_Setup_v{version}.exe"
    versioned_path = DOWNLOADS / versioned_name
    latest_path = DOWNLOADS / "AXON_Setup.exe"

    shutil.copy2(setup, versioned_path)
    shutil.copy2(setup, latest_path)
    return versioned_path, latest_path


def update_version_json(version: str) -> None:
    path = SITE / "version.json"
    payload = {
        "version": version,
        "download_url": "https://runaxon.xyz/downloads/AXON_Setup.exe",
        "winget_id": "Core.AXON",
        "notes": f"AXON {version} — OpenClaw autonomy, TUI, orchestrator",
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def update_versions_json(
    version: str,
    *,
    size_bytes: int,
    sha256: str,
    notes: list[str],
) -> None:
    path = SITE / "versions.json"
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        data = {"updated": "", "releases": []}

    today = date.today().isoformat()
    data["updated"] = today

    for release in data.get("releases", []):
        release["latest"] = False

    data.setdefault("releases", []).insert(
        0,
        {
            "version": version,
            "date": today,
            "channel": "stable",
            "latest": True,
            "size_bytes": size_bytes,
            "sha256": sha256,
            "download_url": "https://runaxon.xyz/downloads/AXON_Setup.exe",
            "download_name": "AXON_Setup.exe",
            "winget": "winget install Core.AXON",
            "notes": notes,
        },
    )

    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def rebuild_zip() -> Path:
    if ZIP_OUT.is_file():
        ZIP_OUT.unlink()

    with zipfile.ZipFile(ZIP_OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(SITE.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.name == "README.txt" and "downloads" in file_path.parts:
                continue
            arcname = file_path.relative_to(SITE).as_posix()
            zf.write(file_path, arcname)
    return ZIP_OUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage AXON release for runaxon.xyz")
    parser.add_argument(
        "--notes",
        nargs="*",
        default=[
            "OpenClaw: /claw on — full tool autonomy in elevated terminal",
            "Cursor-style TUI: task board, streaming, Enter+Up interrupt",
            "/multitask orchestrator — parallel sub-agents",
            "axon claw on|off|status CLI command",
        ],
    )
    args = parser.parse_args()

    version = parse_version()
    setup = find_setup(version)
    digest = sha256_file(setup)
    size = setup.stat().st_size

    versioned_path, latest_path = stage_installer(setup, version)
    update_version_json(version)
    update_versions_json(version, size_bytes=size, sha256=digest, notes=args.notes)
    zip_path = rebuild_zip()

    print(f"Version   : {version}")
    print(f"Installer : {versioned_path.relative_to(ROOT)}")
    print(f"Latest    : {latest_path.relative_to(ROOT)}")
    print(f"SHA-256   : {digest}")
    print(f"Size      : {size:,} bytes")
    print(f"Site zip  : {zip_path.relative_to(ROOT)}")
    print()
    print("Upload: python scripts/upload_site_ftp.py")
    print("   or: deploy/runaxon-site.zip via CityHost file manager")
    return 0


if __name__ == "__main__":
    sys.exit(main())
