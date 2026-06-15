#!/usr/bin/env python3
"""Serve AXON Live Docs on localhost."""

from __future__ import annotations

import argparse
import socket
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def docs_dir(workspace: Path) -> Path:
    return workspace / ".axon" / "docs"


class DocsRequestHandler(SimpleHTTPRequestHandler):
    """Static file handler with JSON content-type for docs.json."""

    def end_headers(self) -> None:
        if self.path.endswith(".json"):
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        if args and "200" in str(args[1]):
            return
        super().log_message(format, *args)


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve AXON Live Docs")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    directory = docs_dir(workspace)
    directory.mkdir(parents=True, exist_ok=True)

    if not (directory / "index.html").is_file():
        print(f"Warning: {directory / 'index.html'} not found. Run docs_gen.py first.")

    if is_port_in_use(args.port, args.host):
        print(f"Port {args.port} already in use — assuming docs server is running.")
        return 0

    handler = partial(DocsRequestHandler, directory=str(directory))
    with ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        url = f"http://{args.host}:{args.port}"
        print(f"Serving AXON docs at {url}")
        print(f"Directory: {directory}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nDocs server stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
