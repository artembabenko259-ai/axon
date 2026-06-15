from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BackupManager:
    """Time Machine — backs up files before write_file overwrites them."""

    workspace: Path = field(default_factory=Path.cwd)
    last_file: Path | None = None
    last_backup: Path | None = None

    @property
    def backup_dir(self) -> Path:
        return self.workspace / ".axon" / "backups"

    def set_workspace(self, workspace: Path) -> None:
        self.workspace = workspace

    def backup_if_exists(self, path: Path) -> Path | None:
        """Save current file contents before overwrite. Returns backup path."""
        if not path.is_file():
            return None

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = path.name.replace(" ", "_")
        backup_path = self.backup_dir / f"{safe_name}_{timestamp}.bak"
        backup_path.write_text(
            path.read_text(encoding="utf-8", errors="replace"),
            encoding="utf-8",
        )
        self.last_file = path
        self.last_backup = backup_path
        return backup_path

    def undo_last(self) -> tuple[bool, str]:
        """Restore the last backed-up file. Returns (success, message)."""
        if self.last_file is None or self.last_backup is None:
            return False, "No file backup available to restore."

        if not self.last_backup.is_file():
            return False, "Backup file is missing."

        try:
            restored = self.last_backup.read_text(encoding="utf-8", errors="replace")
            self.last_file.write_text(restored, encoding="utf-8")
            return True, self.last_file.name
        except OSError as exc:
            return False, f"Restore failed — {exc}"


backup_manager = BackupManager()
