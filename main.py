"""AXON CLI — backward-compatible entry (use `python cli.py` or `axon`)."""

from __future__ import annotations

import sys

from cli import main


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
