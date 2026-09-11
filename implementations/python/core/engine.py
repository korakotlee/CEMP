"""Proposal and two-phase commit editing engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.git_undo import get_git_undo_manager
from core.hasher import compute_content_hash
from core.inspection import get_file_hash, read_file, search_code
from core.patch_cache import PatchCache, PatchStatus
from core.proposals import propose_edit as _propose_edit
from core.proposals import propose_line_edit as _propose_line_edit
from core.storage import atomic_write_file
from core.workspace import resolve_workspace_path
from errors import (
    FileModifiedError,
    PatchAlreadyAppliedError,
    SyntaxErrorCEMP,
)
from verification import get_verification_registry

# Global patch cache singleton
_patch_cache = PatchCache(default_ttl_seconds=900)


def get_patch_cache() -> PatchCache:
    """Access the global in-memory PatchCache instance."""
    return _patch_cache


def propose_edit(
    path: str,
    old_str: str,
    new_str: str,
    expected_occurrences: int = 1,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose an exact string replacement with strict occurrence enforcement."""
    return _propose_edit(
        path=path,
        old_str=old_str,
        new_str=new_str,
        patch_cache=_patch_cache,
        expected_occurrences=expected_occurrences,
        workspace_root=workspace_root,
    )


def propose_line_edit(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    content_hash: str,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose a line-bounded edit protected by CAS hash validation."""
    return _propose_line_edit(
        path=path,
        start_line=start_line,
        end_line=end_line,
        new_content=new_content,
        content_hash=content_hash,
        patch_cache=_patch_cache,
        workspace_root=workspace_root,
    )


def apply_patch(
    patch_id: str,
    tx_id: str | None = None,
    verify_syntax: bool = True,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Atomically commit a staged patch proposal to disk with verification.

    Args:
        patch_id: UUID of the staged patch.
        tx_id: Optional transaction ID.
        verify_syntax: Whether to verify syntax post-write.
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/apply_patch.json.
    """
    proposal = _patch_cache.get(patch_id)
    if proposal.status == PatchStatus.APPLIED:
        raise PatchAlreadyAppliedError(
            message=f"Patch proposal '{patch_id}' has already been applied.",
            data={"patch_id": patch_id},
        )

    resolved_path = resolve_workspace_path(
        proposal.path, workspace_root=workspace_root, must_exist=True
    )
    current_raw = resolved_path.read_text(encoding="utf-8", errors="replace")
    current_hash = compute_content_hash(current_raw)

    if current_hash != proposal.base_hash:
        raise FileModifiedError(
            message=f"File '{proposal.path}' was modified on disk since proposal creation.",
            data={
                "path": proposal.path,
                "base_hash": proposal.base_hash,
                "current_hash": current_hash,
            },
        )

    # 1. Capture pre-write undo snapshot (zero-pollution Git loose blob or fallback)
    root = Path(workspace_root) if workspace_root else None
    undo_mgr = get_git_undo_manager(workspace_root=root)
    snapshot = undo_mgr.snapshot(resolved_path)

    # 2. Perform atomic write to disk
    atomic_write_file(resolved_path, proposal.new_content)

    # 3. Perform post-write syntax verification with auto-rollback
    syntax_info = {"passed": True, "checker": "none"}
    if verify_syntax:
        registry = get_verification_registry()
        syntax_res = registry.check(resolved_path)
        syntax_info = {
            "passed": syntax_res.valid,
            "checker": syntax_res.checker_used,
        }
        if not syntax_res.valid:
            undo_mgr.rollback(snapshot)
            err_msg = "; ".join(syntax_res.errors) if syntax_res.errors else "Syntax error"
            raise SyntaxErrorCEMP(
                message=f"Syntax check failed for '{proposal.path}': {err_msg}",
                data={
                    "path": proposal.path,
                    "checker": syntax_res.checker_used,
                    "errors": syntax_res.errors,
                    "rolled_back": True,
                },
            )

    # 4. Record applied patch in undo history
    undo_mgr.record_applied(
        patch_id=patch_id, target_path=str(resolved_path), snapshot=snapshot
    )
    _patch_cache.mark_applied(patch_id)
    new_hash = compute_content_hash(proposal.new_content)

    return {
        "status": "applied",
        "patch_id": patch_id,
        "path": proposal.path,
        "new_hash": new_hash,
        "syntax_check": syntax_info,
    }


def undo_last(
    path: str | None = None,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Revert the most recent applied patch via zero-pollution Git undo.

    Args:
        path: Optional file path to constrain reversion.
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/undo_last.json.
    """
    resolved_target = None
    if path:
        resolved = resolve_workspace_path(path, workspace_root=workspace_root, must_exist=False)
        resolved_target = str(resolved)

    root = Path(workspace_root) if workspace_root else None
    undo_mgr = get_git_undo_manager(workspace_root=root)
    res = undo_mgr.undo_last(target_path=resolved_target)

    result: dict[str, Any] = {
        "status": res.status,
        "reverted_patch_id": res.reverted_patch_id,
        "reverted_files": res.reverted_files,
    }
    if res.current_hash:
        result["current_hash"] = res.current_hash
    return result


__all__ = [
    "apply_patch",
    "get_file_hash",
    "get_patch_cache",
    "propose_edit",
    "propose_line_edit",
    "read_file",
    "search_code",
    "undo_last",
]
