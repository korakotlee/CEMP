"""Zero-pollution Git-backed undo mechanics and snapshot management."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.hasher import compute_file_hash
from core.storage import atomic_write_bytes
from core.workspace import get_default_workspace_root
from errors import UndoUnavailableError


@dataclass
class UndoSnapshot:
    """Snapshot of a file's state prior to disk modification."""

    path: str
    is_git: bool
    blob_id: Optional[str] = None
    content_bytes: Optional[bytes] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class UndoPatchRecord:
    """Historical record of an applied patch and its undo snapshot."""

    patch_id: str
    target_path: str
    snapshot: UndoSnapshot
    reverted: bool = False


@dataclass
class UndoResult:
    """Structured result returned by undo_last conforming to protocol schema."""

    status: str
    reverted_patch_id: str
    reverted_files: list[str]
    current_hash: Optional[str] = None


class GitUndoManager:
    """Manages pre-edit loose Git snapshots, atomic rollbacks, and undo history."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (
            workspace_root.resolve() if workspace_root else Path.cwd().resolve()
        )
        self._undo_stack: list[UndoPatchRecord] = []

    def _is_git_repo(self, target_dir: Path) -> bool:
        """Check if target directory is within an active Git working tree."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=target_dir,
                capture_output=True,
                text=True,
                check=False,
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except (OSError, ValueError):
            return False

    def snapshot(self, path: Path | str) -> UndoSnapshot:
        """Capture pre-edit file state as a loose Git blob or memory fallback.

        Args:
            path: Target file path.

        Returns:
            UndoSnapshot with Git blob ID or byte buffer.
        """
        target = Path(path).resolve()
        target_dir = target.parent if target.parent.exists() else self.workspace_root

        if self._is_git_repo(target_dir):
            try:
                res = subprocess.run(
                    ["git", "hash-object", "-w", str(target)],
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    return UndoSnapshot(
                        path=str(target),
                        is_git=True,
                        blob_id=res.stdout.strip(),
                    )
            except OSError:
                pass

        # Fallback for non-git workspaces or failed git plumbing
        raw_bytes = target.read_bytes() if target.exists() else b""
        return UndoSnapshot(
            path=str(target),
            is_git=False,
            content_bytes=raw_bytes,
        )

    def rollback(self, snapshot: UndoSnapshot) -> Path:
        """Restore file to snapshot state via atomic file replacement.

        Args:
            snapshot: Undo snapshot containing original state.

        Returns:
            Path to restored file.
        """
        target = Path(snapshot.path).resolve()
        target_dir = target.parent if target.parent.exists() else self.workspace_root

        if snapshot.is_git and snapshot.blob_id:
            res = subprocess.run(
                ["git", "cat-file", "-p", snapshot.blob_id],
                cwd=target_dir,
                capture_output=True,
                check=True,
            )
            atomic_write_bytes(target, res.stdout)
        else:
            atomic_write_bytes(target, snapshot.content_bytes or b"")

        return target

    def record_applied(
        self, patch_id: str, target_path: str, snapshot: UndoSnapshot
    ) -> None:
        """Push an applied patch record onto the LIFO undo stack."""
        resolved = str(Path(target_path).resolve())
        self._undo_stack.append(
            UndoPatchRecord(
                patch_id=patch_id,
                target_path=resolved,
                snapshot=snapshot,
                reverted=False,
            )
        )

    def undo_last(self, target_path: Optional[str] = None) -> UndoResult:
        """Revert the most recent applied patch, optionally filtered by path.

        Args:
            target_path: Optional path to constrain which patch to undo.

        Returns:
            UndoResult with reversion details and restored hash.

        Raises:
            UndoUnavailableError: If no eligible patch exists to undo.
        """
        resolved_filter = (
            str(Path(target_path).resolve()) if target_path else None
        )

        for record in reversed(self._undo_stack):
            if record.reverted:
                continue
            if resolved_filter and record.target_path != resolved_filter:
                continue

            # Eligible record found
            self.rollback(record.snapshot)
            record.reverted = True

            current_hash = (
                compute_file_hash(record.target_path)
                if Path(record.target_path).exists()
                else None
            )

            # Report path relative to workspace if within workspace
            try:
                rel_path = str(
                    Path(record.target_path).relative_to(self.workspace_root)
                )
            except ValueError:
                rel_path = Path(record.target_path).name

            return UndoResult(
                status="reverted",
                reverted_patch_id=record.patch_id,
                reverted_files=[rel_path],
                current_hash=current_hash,
            )

        target_desc = f" for {target_path}" if target_path else ""
        raise UndoUnavailableError(
            f"No applied patch available to undo{target_desc}."
        )


    def clear(self) -> None:
        """Clear all undo records from history."""
        self._undo_stack.clear()


_DEFAULT_UNDO_MANAGER: Optional[GitUndoManager] = None


def get_git_undo_manager(workspace_root: Optional[Path] = None) -> GitUndoManager:
    """Retrieve or initialize the global GitUndoManager instance."""
    global _DEFAULT_UNDO_MANAGER
    effective_root = (
        workspace_root.resolve()
        if workspace_root
        else get_default_workspace_root()
    )
    if (
        _DEFAULT_UNDO_MANAGER is None
        or _DEFAULT_UNDO_MANAGER.workspace_root != effective_root
    ):
        _DEFAULT_UNDO_MANAGER = GitUndoManager(effective_root)
    return _DEFAULT_UNDO_MANAGER

