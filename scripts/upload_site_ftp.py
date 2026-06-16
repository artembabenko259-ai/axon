"""Upload deploy/site/ to CityHost FTP (runaxon.xyz root)."""

from __future__ import annotations

import argparse
import ftplib
import os
import sys
from pathlib import Path

HOST = os.environ.get("AXON_FTP_HOST", "cruze.cityhost.com.ua")
USER = os.environ.get("AXON_FTP_USER", "ch150dbf44")
PASSWORD = os.environ.get("AXON_FTP_PASSWORD", "")
LOCAL_ROOT = Path(__file__).resolve().parents[1] / "deploy" / "site"
ENV_FILE = Path(__file__).resolve().parents[1] / "deploy" / ".ftp.env"
SKIP_NAMES = {".git", ".DS_Store", "Thumbs.db", "README.txt"}

RELEASE_FILES = (
    "version.json",
    "versions.json",
    "downloads/AXON_Setup.exe",
    "downloads/AXON_Setup_v1.0.1.exe",
)

PROVIX_FILES = (
    "index.html",
    "provix/index.html",
    "provix/style.css",
    "provix/version.json",
    "provix/install.ps1",
    "downloads/provix/Provix-Setup.exe",
    "downloads/provix/Provix-Setup-1.3.5.exe",
)


def _load_env_file() -> None:
    if not ENV_FILE.is_file():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _ftp_cwd(ftp: ftplib.FTP, path: str) -> None:
    ftp.cwd("/")
    for part in [p for p in path.replace("\\", "/").split("/") if p]:
        try:
            ftp.cwd(part)
        except ftplib.error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


def _upload_file(ftp: ftplib.FTP, local: Path, remote_rel: str) -> None:
    remote_rel = remote_rel.replace("\\", "/")
    remote_dir = str(Path(remote_rel).parent).replace("\\", "/")
    remote_name = Path(remote_rel).name

    base = ftp.pwd()
    if remote_dir and remote_dir != ".":
        _ftp_cwd(ftp, f"{base}/{remote_dir}".replace("//", "/"))
    else:
        ftp.cwd(base)

    size = local.stat().st_size
    print(f"UP  {remote_rel} ({size // 1024} KB)...", flush=True)

    sent = 0

    def _progress(chunk: bytes) -> None:
        nonlocal sent
        sent += len(chunk)
        if size > 512 * 1024:
            pct = sent * 100 // size
            if pct % 10 == 0:
                print(f"    {remote_rel}: {pct}%", flush=True)

    with local.open("rb") as handle:
        ftp.storbinary(f"STOR {remote_name}", handle, blocksize=256 * 1024, callback=_progress)
    print(f"OK  {remote_rel}", flush=True)


def _iter_local_files(local_root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(local_root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in SKIP_NAMES:
            continue
        files.append(path)
    return files


def upload_release(ftp: ftplib.FTP) -> None:
    for rel in RELEASE_FILES:
        local = LOCAL_ROOT / rel
        if not local.is_file():
            raise FileNotFoundError(f"Missing release file: {local}")
        _upload_file(ftp, local, rel)


def upload_provix(ftp: ftplib.FTP) -> None:
    for rel in PROVIX_FILES:
        local = LOCAL_ROOT / rel
        if not local.is_file():
            raise FileNotFoundError(f"Missing Provix file: {local}")
        _upload_file(ftp, local, rel)


def upload_tree(ftp: ftplib.FTP, local_root: Path) -> None:
    for local in _iter_local_files(local_root):
        rel = local.relative_to(local_root).as_posix()
        _upload_file(ftp, local, rel)


def probe(ftp: ftplib.FTP) -> None:
    print(f"PWD: {ftp.pwd()}", flush=True)
    print("Root listing:", flush=True)
    for name in ftp.nlst()[:40]:
        print(f"  {name}", flush=True)

    candidates = (
        "www/runaxon.xyz",
        "www",
        "runaxon.xyz",
        "public_html",
        "domains/runaxon.xyz/public_html",
    )
    for candidate in candidates:
        try:
            _ftp_cwd(ftp, candidate)
            print(f"\n[{candidate}] -> {ftp.pwd()}", flush=True)
            names = ftp.nlst()
            print("  " + ", ".join(names[:20]), flush=True)
            if "version.json" in names:
                print(f"  version.json size: {ftp.size('version.json')}", flush=True)
        except Exception as exc:
            print(f"\n[{candidate}] skip: {exc}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload runaxon.xyz site via FTP")
    parser.add_argument(
        "--release-only",
        action="store_true",
        help="Upload only version.json + installer (fast)",
    )
    parser.add_argument(
        "--provix",
        action="store_true",
        help="Upload Provix page + installer (~100 MB)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Upload entire deploy/site/ tree",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="List FTP paths (find web root)",
    )
    parser.add_argument(
        "--remote-root",
        default=os.environ.get("AXON_FTP_REMOTE", "www/runaxon.xyz"),
        help="Remote web root relative to FTP home (default: www/runaxon.xyz)",
    )
    args = parser.parse_args()

    _load_env_file()
    password = os.environ.get("AXON_FTP_PASSWORD", PASSWORD)
    if not password:
        print("Set AXON_FTP_PASSWORD or create deploy/.ftp.env", file=sys.stderr)
        return 1
    if not LOCAL_ROOT.is_dir():
        print(f"Missing folder: {LOCAL_ROOT}", file=sys.stderr)
        return 1

    print(f"Connecting to {HOST} as {USER}...", flush=True)
    ftp = ftplib.FTP()
    ftp.connect(HOST, 21, timeout=60)
    ftp.login(USER, password)
    ftp.set_pasv(True)
    print(ftp.getwelcome(), flush=True)

    if args.probe:
        probe(ftp)
        ftp.quit()
        return 0

    if args.remote_root:
        _ftp_cwd(ftp, args.remote_root)
        print(f"Remote root: {ftp.pwd()}", flush=True)

    try:
        if args.full:
            upload_tree(ftp, LOCAL_ROOT)
        elif args.provix:
            upload_provix(ftp)
        elif args.release_only:
            upload_release(ftp)
        else:
            upload_release(ftp)
    finally:
        ftp.quit()

    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
