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


def build_review_prompt(workspace: Path | None = None) -> tuple[str, str | None]:
    """
    Collect git status + diff and build an LLM review prompt.

    Returns (prompt, error_message).
    """
    cwd = workspace or Path.cwd()
    if not (cwd / ".git").exists():
        return "", "AXON: Not a git repository. Run /review inside a git project."

    status = _run_git(["status"], cwd)
    diff = _run_git(["diff"], cwd)
    if diff == "(no output)":
        diff = _run_git(["diff", "--cached"], cwd)

    prompt = (
        "Perform a code review of the current working tree changes.\n"
        "Find bugs, security issues, regressions, and code smells.\n"
        "Be specific — reference files and lines when possible.\n"
        "Structure: Summary → Critical issues → Suggestions → Positives.\n\n"
        f"## git status\n```\n{status}\n```\n\n"
        f"## git diff\n```\n{diff}\n```"
    )
    return prompt, None
