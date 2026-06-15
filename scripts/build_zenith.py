#!/usr/bin/env python3
"""Build Zenith (Next.js standalone) + portable Node for the AXON installer."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZENITH_SRC = ROOT / "zenith-web"
BUILD_DIR = ROOT / "build"
BUNDLE_DIR = BUILD_DIR / "bundle-staging"
STAGE_ZENITH = BUNDLE_DIR / "zenith-web"
STAGE_NODE = BUNDLE_DIR / "node"
NODE_VERSION = "20.19.3"
NODE_ZIP_NAME = f"node-v{NODE_VERSION}-win-x64"
NODE_CACHE = BUILD_DIR / "node-runtime" / NODE_ZIP_NAME
NODE_URL = f"https://nodejs.org/dist/v{NODE_VERSION}/{NODE_ZIP_NAME}.zip"


def run_npm_build() -> None:
    if not (ZENITH_SRC / "package.json").is_file():
        raise SystemExit(f"zenith-web not found at {ZENITH_SRC}")

    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found on PATH — install Node.js 20+ to build Zenith.")

    print("Zenith: npm install ...")
    subprocess.run(
        ["npm", "install"],
        cwd=str(ZENITH_SRC),
        shell=sys.platform == "win32",
        check=True,
    )
    print("Zenith: npm run build ...")
    subprocess.run(
        ["npm", "run", "build"],
        cwd=str(ZENITH_SRC),
        shell=sys.platform == "win32",
        check=True,
    )


def stage_standalone() -> None:
    standalone = ZENITH_SRC / ".next" / "standalone"
    static_dir = ZENITH_SRC / ".next" / "static"
    public_dir = ZENITH_SRC / "public"

    if not (standalone / "server.js").is_file():
        raise SystemExit("Next.js standalone build missing .next/standalone/server.js")

    if STAGE_ZENITH.exists():
        shutil.rmtree(STAGE_ZENITH)
    STAGE_ZENITH.mkdir(parents=True)

    print(f"Zenith: staging standalone -> {STAGE_ZENITH}")
    shutil.copytree(standalone, STAGE_ZENITH, dirs_exist_ok=True)

    dest_static = STAGE_ZENITH / ".next" / "static"
    dest_static.parent.mkdir(parents=True, exist_ok=True)
    if dest_static.exists():
        shutil.rmtree(dest_static)
    shutil.copytree(static_dir, dest_static)

    if public_dir.is_dir():
        dest_public = STAGE_ZENITH / "public"
        if dest_public.exists():
            shutil.rmtree(dest_public)
        shutil.copytree(public_dir, dest_public)


def ensure_portable_node() -> None:
    STAGE_NODE.mkdir(parents=True, exist_ok=True)
    staged_exe = STAGE_NODE / "node.exe"
    if staged_exe.is_file():
        print(f"Zenith: reusing staged {staged_exe}")
        return

    extracted = NODE_CACHE
    node_exe = extracted / "node.exe"
    if not node_exe.is_file():
        archive = NODE_CACHE.with_suffix(".zip")
        if not archive.is_file():
            print(f"Zenith: downloading Node.js {NODE_VERSION} ...")
            archive.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(NODE_URL, archive)
        print(f"Zenith: extracting {archive.name} ...")
        if extracted.exists():
            shutil.rmtree(extracted)
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(extracted.parent)

    if not node_exe.is_file():
        raise SystemExit(f"node.exe not found after extract: {node_exe}")

    shutil.copy2(node_exe, staged_exe)
    print(f"Zenith: staged portable node -> {staged_exe}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Zenith for AXON installer")
    parser.add_argument("--skip-npm", action="store_true", help="Only stage existing .next build")
    args = parser.parse_args()

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    if not args.skip_npm:
        run_npm_build()
    stage_standalone()
    ensure_portable_node()

    print()
    print("=" * 72)
    print("Zenith build complete")
    print("=" * 72)
    print(f"  panel : {STAGE_ZENITH}")
    print(f"  node  : {STAGE_NODE / 'node.exe'}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
