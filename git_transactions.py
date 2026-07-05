"""Git transactional checkpoints manager for AXON (auto-commit and safe rollback)."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitTransactionManager:
    """Manages transaction-safe checkpoints in Git to prevent code corruption."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace = Path(workspace_path)
        self.is_git = self._check_is_git()

    def _check_is_git(self) -> bool:
        # Check if .git exists in workspace or parents
        curr = self.workspace
        while curr != curr.parent:
            if (curr / ".git").is_dir():
                return True
            curr = curr.parent
        return False

    def has_changes(self) -> bool:
        if not self.is_git:
            return False
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.workspace,
            capture_output=True,
            text=True
        )
        return len(res.stdout.strip()) > 0

    def create_checkpoint(self, name: str) -> str | None:
        """Stages all changes and commits a temporary checkpoint. Returns commit hash."""
        if not self.is_git:
            return None
        
        # Stage all changes
        subprocess.run(["git", "add", "."], cwd=self.workspace, capture_output=True)
        
        # Commit
        res = subprocess.run(
            ["git", "commit", "-m", f"AXON_CHECKPOINT: {name}"],
            cwd=self.workspace,
            capture_output=True,
            text=True
        )
        if res.returncode == 0:
            hash_res = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.workspace,
                capture_output=True,
                text=True
            )
            return hash_res.stdout.strip()
        return None

    def rollback(self, checkpoint_hash: str) -> bool:
        """Rollbacks working tree and index to specified commit hash, cleaning untracked files."""
        if not self.is_git or not checkpoint_hash:
            return False
        
        # Reset hard to checkpoint
        res_reset = subprocess.run(
            ["git", "reset", "--hard", checkpoint_hash],
            cwd=self.workspace,
            capture_output=True
        )
        # Clean untracked files
        subprocess.run(["git", "clean", "-fd"], cwd=self.workspace, capture_output=True)
        
        return res_reset.returncode == 0

    def finalize(self, checkpoint_hash: str, commit_message: str) -> bool:
        """Amends the checkpoint commit with a clean, conventional commit message."""
        if not self.is_git or not checkpoint_hash:
            return False
        
        res = subprocess.run(
            ["git", "commit", "--amend", "-m", commit_message],
            cwd=self.workspace,
            capture_output=True
        )
        return res.returncode == 0
