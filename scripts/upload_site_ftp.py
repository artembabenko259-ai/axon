"""Upload deploy/site/ to CityHost FTP (runaxon.xyz root)."""
from __future__ import annotations

import ftplib
import os
import sys
from pathlib import Path

HOST = os.environ.get("AXON_FTP_HOST", "cruze.cityhost.com.ua")
USER = os.environ.get("AXON_FTP_USER", "ch150dbf44")
PASSWORD = os.environ.get("AXON_FTP_PASSWORD", "")
LOCAL_ROOT = Path(__file__).resolve().parents[1] / "deploy" / "site"
SKIP_NAMES = {".git", ".DS_Store", "Thumbs.db"}


def ensure_remote_dir(ftp: ftplib.FTP, remote_dir: str) -> None:
    parts = [p for p in remote_dir.replace("\\", "/").split("/") if p]
    path = ""
    for part in parts:
        path = f"{path}/{part}"
        try:
            ftp.cwd(path)
        except ftplib.error_perm:
            ftp.mkd(path)
            ftp.cwd(path)
    for _ in parts:
        ftp.cwd("..")


def upload_tree(ftp: ftplib.FTP, local: Path, remote: str) -> None:
    ensure_remote_dir(ftp, remote)
    for entry in sorted(local.iterdir()):
        if entry.name in SKIP_NAMES:
            continue
        remote_path = f"{remote}/{entry.name}".replace("\\", "/")
        if entry.is_dir():
            upload_tree(ftp, entry, remote_path)
            continue
        with entry.open("rb") as handle:
            print(f"UP  {remote_path} ({entry.stat().st_size // 1024} KB)")
            ftp.storbinary(f"STOR {remote_path}", handle)


def main() -> int:
    if not PASSWORD:
        print("Set AXON_FTP_PASSWORD environment variable.", file=sys.stderr)
        return 1
    if not LOCAL_ROOT.is_dir():
        print(f"Missing folder: {LOCAL_ROOT}", file=sys.stderr)
        return 1

    print(f"Connecting to {HOST} as {USER}...")
    ftp = ftplib.FTP(HOST, timeout=120)
    ftp.login(USER, PASSWORD)
    ftp.set_pasv(True)
    print(ftp.getwelcome())

    upload_tree(ftp, LOCAL_ROOT, "")
    ftp.quit()
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
