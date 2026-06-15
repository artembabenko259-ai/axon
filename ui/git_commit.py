from __future__ import annotations

import subprocess
from pathlib import Path


def _run_git(args: list[str], cwd: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return output.strip() or "(no output)"
    except FileNotFoundError:
        return "(git is not installed or not on PATH)"
    except subprocess.TimeoutExpired:
        return "(git command timed out)"
    except OSError as exc:
        return f"(git error: {exc})"


def collect_git_changes(workspace: Path | None = None) -> tuple[str, str, str | None]:
    """Return git status, diff, and optional error."""
    cwd = workspace or Path.cwd()
    if not (cwd / ".git").exists():
        return "", "", "AXON: Not a git repository. Run /commit inside a git project."

    status = _run_git(["status"], cwd)
    diff = _run_git(["diff"], cwd)
    if diff == "(no output)":
        diff = _run_git(["diff", "--cached"], cwd)

    if status == "(no output)" and diff == "(no output)":
        return status, diff, "AXON: Nothing to commit — working tree is clean."

    return status, diff, None


def run_git_commit(message: str, workspace: Path | None = None) -> tuple[bool, str]:
    """Execute git commit -am with the given message."""
    cwd = workspace or Path.cwd()
    try:
        proc = subprocess.run(
            ["git", "commit", "-am", message],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode == 0:
            return True, output.strip() or "Commit created."
        return False, output.strip() or f"git commit failed (exit {proc.returncode})"
    except FileNotFoundError:
        return False, "git is not installed or not on PATH"
    except subprocess.TimeoutExpired:
        return False, "git commit timed out"
    except OSError as exc:
        return False, f"git commit error — {exc}"
