#!/usr/bin/env python3
"""
DEPRECATED: Portable ZIP packaging replaced by PyInstaller + Inno Setup.
See BUILD_GUIDE.md and scripts/build_exe.py.

Legacy script — gathers production files into axon-portable.zip.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "dist"
ZIP_NAME = "axon-portable.zip"
WINGET_INSTALLER = ROOT / "winget" / "Artem.AXON.installer.yaml"

# Directories copied recursively (relative to ROOT).
INCLUDE_DIRS = (
    "skills",
    "ui",
    "scripts",
    ".axon/skills",
    ".axon/docs",
)

# Single files at repository root.
INCLUDE_FILES = (
    "main.py",
    "bridge.py",
    "llm_client.py",
    "skills_manager.py",
    "command_parser.py",
    "agent_manager.py",
    "backup_manager.py",
    "config_store.py",
    "task_manager.py",
    "controller.py",
    "commands.py",
    "requirements.txt",
    "README.md",
    ".env.example",
    "axon.bat",
)

LOCALE_SOURCES = (
    ROOT / "zenith-web" / "locales",
)

EXCLUDE_DIR_NAMES = frozenset(
    {
        ".git",
        ".cursor",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".next",
        "dist",
        "agent-tools",
        "backups",
    }
)

EXCLUDE_FILE_NAMES = frozenset({".env", ".DS_Store", "Thumbs.db"})

EXCLUDE_FILE_SUFFIXES = frozenset({".pyc", ".pyo", ".log", ".bak"})

EXCLUDE_SCRIPT_PREFIXES = ("_test_",)


def parse_version() -> str:
    branding = ROOT / "ui" / "branding.py"
    if branding.is_file():
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', branding.read_text(encoding="utf-8"))
        if match:
            return match.group(1)
    return "1.0.0"


def should_exclude_path(path: Path) -> bool:
    for part in path.parts:
        if part in EXCLUDE_DIR_NAMES:
            return True
    if path.name in EXCLUDE_FILE_NAMES:
        return True
    if path.suffix.lower() in EXCLUDE_FILE_SUFFIXES:
        return True
    if path.parent.name == "scripts" and path.name.startswith(EXCLUDE_SCRIPT_PREFIXES):
        return True
    return False


def copy_tree(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        if should_exclude_path(rel):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(f"Required file missing: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def stage_locales(staging: Path) -> None:
    """Mirror Zenith locale JSON into .axon/locales/ for portable documentation."""
    locales_root = staging / ".axon" / "locales"
    locales_root.mkdir(parents=True, exist_ok=True)

    main_locales = ROOT / "zenith-web" / "locales"
    for path in sorted(main_locales.glob("*.json")):
        shutil.copy2(path, locales_root / path.name)

    mastery_src = main_locales / "skills-mastery"
    if mastery_src.is_dir():
        mastery_dst = locales_root / "skills-mastery"
        mastery_dst.mkdir(parents=True, exist_ok=True)
        for path in sorted(mastery_src.glob("*.json")):
            shutil.copy2(path, mastery_dst / path.name)


def build_staging_dir(staging: Path) -> None:
    staging.mkdir(parents=True, exist_ok=True)

    for name in INCLUDE_FILES:
        copy_file(ROOT / name, staging / name)

    for rel in INCLUDE_DIRS:
        src = ROOT / rel
        dst = staging / rel
        if src.is_dir():
            copy_tree(src, dst)
        elif src.is_file():
            copy_file(src, dst)

    stage_locales(staging)


def create_zip(staging: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(staging.rglob("*")):
            if not file_path.is_file():
                continue
            arcname = file_path.relative_to(staging).as_posix()
            zf.write(file_path, arcname)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def patch_installer_hash(sha256: str, *, apply: bool) -> None:
    if not WINGET_INSTALLER.is_file():
        return
    text = WINGET_INSTALLER.read_text(encoding="utf-8")
    updated = re.sub(
        r"(InstallerSha256:\s*)(?:PLACEHOLDER_HASH|[A-Fa-f0-9]{64})",
        rf"\g<1>{sha256}",
        text,
        count=1,
    )
    if apply and updated != text:
        WINGET_INSTALLER.write_text(updated, encoding="utf-8")


def print_instructions(sha256: str, zip_path: Path, version: str) -> None:
    rel_zip = zip_path.relative_to(ROOT)
    rel_manifest = WINGET_INSTALLER.relative_to(ROOT)

    print()
    print("=" * 72)
    print("AXON portable release package ready")
    print("=" * 72)
    print(f"  Version : {version}")
    print(f"  Archive : {rel_zip}")
    print(f"  SHA-256 : {sha256}")
    print()
    print("Paste the SHA-256 into:")
    print(f"  {rel_manifest}")
    print("  field: InstallerSha256")
    print()
    print("Update InstallerUrl to your GitHub release asset, for example:")
    print(
        f"  https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO/releases/download/v{version}/axon-portable.zip"
    )
    print()
    print("Local Winget test:")
    print("  See winget/TEST_GUIDE.md")
    print("  winget validate --manifest <manifest-only-folder>")
    print("  winget install --manifest <manifest-only-folder>")
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build AXON portable Winget release ZIP.")
    parser.add_argument(
        "--patch-manifest",
        action="store_true",
        help="Write computed SHA-256 into winget/Artem.AXON.installer.yaml",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DIST_DIR / ZIP_NAME,
        help=f"Output ZIP path (default: dist/{ZIP_NAME})",
    )
    args = parser.parse_args()

    version = parse_version()
    zip_path = args.output if args.output.is_absolute() else ROOT / args.output

    with tempfile.TemporaryDirectory(prefix="axon-release-") as tmp:
        staging = Path(tmp) / "axon-portable"
        print(f"Staging release v{version}...")
        build_staging_dir(staging)
        print(f"Creating {zip_path.relative_to(ROOT)}...")
        create_zip(staging, zip_path)

    sha256 = sha256_file(zip_path)
    patch_installer_hash(sha256, apply=args.patch_manifest)
    print_instructions(sha256, zip_path, version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
