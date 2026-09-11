"""Multi-file transaction manager and atomic batch commit coordinator."""

from __future__ import annotations

import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.git_undo import get_git_undo_manager
from core.hasher import compute_content_hash
from core.patch_cache import PatchCache, PatchProposal
from core.storage import atomic_write_file
from core.workspace import resolve_workspace_path
from errors import (
    FileModifiedError,
    RollbackTriggeredError,
    TransactionActiveError,
    TransactionNotFoundError,
)
from verification import get_verification_registry


@dataclass
class Transaction:
    """Represents an active multi-file transaction staging session."""

    tx_id: str
    isolation_level: str
    created_at: float
    ttl_seconds: int
    staging_dir: Path
    staged_patches: dict[str, PatchProposal] = field(default_factory=dict)
    staged_files: dict[str, str] = field(default_factory=dict)  # path -> patch_id

    @property
    def is_expired(self) -> bool:
        """Check if the transaction has exceeded its time-to-live."""
        return (time.time() - self.created_at) > self.ttl_seconds


class TransactionManager:
    """Coordinates lifecycle, staging, and atomic batch commit for transactions."""

    def __init__(self, default_ttl_seconds: int = 1800) -> None:
        self._default_ttl_seconds = default_ttl_seconds
        self._active_transaction: Transaction | None = None

    def _prune_if_expired(self) -> None:
        if self._active_transaction and self._active_transaction.is_expired:
            self._cleanup_staging(self._active_transaction)
            self._active_transaction = None

    def _cleanup_staging(self, tx: Transaction) -> None:
        if tx.staging_dir and tx.staging_dir.exists():
            shutil.rmtree(tx.staging_dir, ignore_errors=True)

    def begin_transaction(
        self,
        isolation_level: str = "snapshot",
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Begin a new atomic multi-file transaction session."""
        self._prune_if_expired()
        if self._active_transaction is not None:
            raise TransactionActiveError(
                message=f"A transaction '{self._active_transaction.tx_id}' is already active.",
                data={"active_tx_id": self._active_transaction.tx_id},
            )

        ttl = ttl_seconds or self._default_ttl_seconds
        tx_id = str(uuid.uuid4())
        staging_dir = Path(tempfile.mkdtemp(prefix=f"cemp_tx_{tx_id}_"))

        self._active_transaction = Transaction(
            tx_id=tx_id,
            isolation_level=isolation_level,
            created_at=time.time(),
            ttl_seconds=ttl,
            staging_dir=staging_dir,
        )

        return {
            "status": "open",
            "tx_id": tx_id,
            "expires_in_seconds": ttl,
        }

    def get_transaction(self, tx_id: str) -> Transaction:
        """Retrieve active transaction by tx_id, rejecting unknown or expired IDs."""
        self._prune_if_expired()
        if not self._active_transaction or self._active_transaction.tx_id != tx_id:
            raise TransactionNotFoundError(
                message=f"Transaction '{tx_id}' not found or expired.",
                data={"tx_id": tx_id},
            )
        return self._active_transaction

    def stage_patch(
        self,
        tx_id: str,
        proposal: PatchProposal,
        workspace_root: Path | str | None = None,
    ) -> dict[str, Any]:
        """Stage a patch proposal inside the isolated transaction directory."""
        tx = self.get_transaction(tx_id)

        # Write proposal content into transaction staging directory
        staged_target = tx.staging_dir / proposal.path
        staged_target.parent.mkdir(parents=True, exist_ok=True)
        staged_target.write_text(proposal.new_content, encoding="utf-8")

        tx.staged_patches[proposal.patch_id] = proposal
        tx.staged_files[proposal.path] = proposal.patch_id

        return {
            "status": "staged",
            "patch_id": proposal.patch_id,
            "path": proposal.path,
        }

    def commit_transaction(
        self,
        tx_id: str,
        patch_cache: PatchCache,
        verify_syntax: bool = True,
        workspace_root: Path | str | None = None,
    ) -> dict[str, Any]:
        """Atomically commit all staged patches across files with CAS and rollback checks."""
        tx = self.get_transaction(tx_id)
        root = Path(workspace_root) if workspace_root else None
        undo_mgr = get_git_undo_manager(workspace_root=root)

        # Phase 1: Verify CAS baseline hash for all staged files before altering any file
        file_targets: list[tuple[PatchProposal, Path]] = []
        for proposal in tx.staged_patches.values():
            resolved = resolve_workspace_path(
                proposal.path, workspace_root=workspace_root, must_exist=True
            )
            current_raw = resolved.read_text(encoding="utf-8", errors="replace")
            current_hash = compute_content_hash(current_raw)
            if current_hash != proposal.base_hash:
                raise FileModifiedError(
                    message=f"File '{proposal.path}' modified on disk since proposal creation.",
                    data={
                        "path": proposal.path,
                        "base_hash": proposal.base_hash,
                        "current_hash": current_hash,
                    },
                )
            file_targets.append((proposal, resolved))

        # Phase 2: Capture undo snapshots for all targets
        snapshots: list[tuple[PatchProposal, Path, Any]] = []
        for proposal, resolved in file_targets:
            snap = undo_mgr.snapshot(resolved)
            snapshots.append((proposal, resolved, snap))

        # Phase 3: Perform atomic writes to live files
        written_snapshots: list[tuple[PatchProposal, Path, Any]] = []
        try:
            for proposal, resolved, snap in snapshots:
                atomic_write_file(resolved, proposal.new_content)
                written_snapshots.append((proposal, resolved, snap))

            # Phase 4: Post-write syntax validation across modified files
            if verify_syntax:
                registry = get_verification_registry()
                for proposal, resolved, _ in written_snapshots:
                    check_res = registry.check(resolved)
                    if not check_res.valid:
                        err_text = "; ".join(check_res.errors) or "Syntax check failed"
                        raise RollbackTriggeredError(
                            message=f"Verification failed on '{proposal.path}': {err_text}",
                            data={
                                "path": proposal.path,
                                "checker": check_res.checker_used,
                                "errors": check_res.errors,
                                "rolled_back": True,
                            },
                        )
        except Exception as exc:
            # Automatic batch rollback for all written files
            for _, resolved, snap in written_snapshots:
                undo_mgr.rollback(snap)
            self._cleanup_staging(tx)
            self._active_transaction = None
            if isinstance(exc, RollbackTriggeredError):
                raise
            raise RollbackTriggeredError(
                message=f"Transaction batch commit failed and rolled back: {exc}",
                data={"errors": [str(exc)], "rolled_back": True},
            ) from exc

        # Phase 5: Finalize applied status and compute fresh digests
        file_hashes: dict[str, str] = {}
        for proposal, resolved, snap in written_snapshots:
            undo_mgr.record_applied(proposal.patch_id, str(resolved), snap)
            patch_cache.mark_applied(proposal.patch_id)
            file_hashes[proposal.path] = compute_content_hash(proposal.new_content)

        files_updated = list(file_hashes.keys())
        self._cleanup_staging(tx)
        self._active_transaction = None

        return {
            "status": "committed",
            "tx_id": tx_id,
            "files_updated": files_updated,
            "file_hashes": file_hashes,
        }

    def rollback_transaction(
        self,
        tx_id: str,
        workspace_root: Path | str | None = None,
    ) -> dict[str, Any]:
        """Abort open transaction, discard staged patches, and clean temporary storage."""
        tx = self.get_transaction(tx_id)
        discarded_count = len(tx.staged_patches)
        self._cleanup_staging(tx)
        self._active_transaction = None

        return {
            "status": "rolled_back",
            "tx_id": tx_id,
            "discarded_patches_count": discarded_count,
        }

    def reset(self) -> None:
        """Reset active transaction state and cleanup temporary directory."""
        if self._active_transaction:
            self._cleanup_staging(self._active_transaction)
            self._active_transaction = None


# Global transaction manager singleton
_tx_manager = TransactionManager(default_ttl_seconds=1800)


def get_transaction_manager() -> TransactionManager:
    """Access the global TransactionManager instance."""
    return _tx_manager


def reset_transaction_manager() -> None:
    """Reset the global transaction manager singleton."""
    _tx_manager.reset()
