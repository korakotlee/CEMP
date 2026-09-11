"""Proposal and two-phase commit editing engine."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from core.hasher import compute_content_hash, normalize_line_endings
from core.inspection import get_file_hash, read_file, search_code
from core.patch_cache import PatchCache, PatchStatus
from core.storage import atomic_write_file
from core.workspace import resolve_workspace_path
from errors import (
    FileModifiedError,
    InvalidRangeError,
    NoMatchError,
    OccurrenceMismatchError,
    PatchAlreadyAppliedError,
    StaleHashError,
)

# Global patch cache singleton
_patch_cache = PatchCache(default_ttl_seconds=900)


def get_patch_cache() -> PatchCache:
    """Access the global in-memory PatchCache instance."""
    return _patch_cache


def _generate_unified_diff(
    original_text: str,
    new_text: str,
    path: str,
) -> str:
    """Generate a standard unified diff preview between two texts."""
    orig_lines = [line + "\n" for line in original_text.splitlines()]
    new_lines = [line + "\n" for line in new_text.splitlines()]
    diff = difflib.unified_diff(
        orig_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff)


def propose_edit(
    path: str,
    old_str: str,
    new_str: str,
    expected_occurrences: int = 1,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose an exact string replacement with strict occurrence enforcement.

    Args:
        path: Target file path within workspace.
        old_str: Exact substring to be replaced.
        new_str: Replacement substring.
        expected_occurrences: Expected number of matches (default: 1).
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/propose_edit.json.
    """
    resolved_path = resolve_workspace_path(path, workspace_root=workspace_root, must_exist=True)
    raw_text = resolved_path.read_text(encoding="utf-8", errors="replace")
    normalized_text = normalize_line_endings(raw_text)
    base_hash = compute_content_hash(raw_text)

    count = normalized_text.count(old_str)
    if count == 0:
        raise NoMatchError(
            message=f"Target string not found in '{path}'.",
            data={"path": path, "old_str": old_str},
        )

    if count != expected_occurrences:
        # Collect line numbers and previews for each occurrence
        matches: list[dict[str, Any]] = []
        for idx, line in enumerate(normalized_text.splitlines(), start=1):
            if old_str in line:
                matches.append({"line": idx, "preview": line})
        raise OccurrenceMismatchError(
            message=f"String matched {count} times; expected exactly {expected_occurrences}.",
            data={
                "path": path,
                "expected_occurrences": expected_occurrences,
                "actual_occurrences": count,
                "matches": matches,
            },
        )

    new_content = normalized_text.replace(old_str, new_str)
    diff_preview = _generate_unified_diff(normalized_text, new_content, path)

    proposal = _patch_cache.store(
        path=path,
        base_hash=base_hash,
        new_content=new_content,
        diff=diff_preview,
    )

    return {
        "status": "ok",
        "patch_id": proposal.patch_id,
        "path": path,
        "match_count": count,
        "diff_preview": diff_preview,
        "expires_in_seconds": proposal.ttl_seconds,
    }


def propose_line_edit(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    content_hash: str,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose a line-bounded edit protected by CAS hash validation.

    Args:
        path: Target file path within workspace.
        start_line: 1-indexed start line number.
        end_line: 1-indexed inclusive end line number.
        new_content: Replacement text for the specified line block.
        content_hash: SHA-256 hash expected from prior read_file.
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/propose_line_edit.json.
    """
    resolved_path = resolve_workspace_path(path, workspace_root=workspace_root, must_exist=True)
    raw_text = resolved_path.read_text(encoding="utf-8", errors="replace")
    live_hash = compute_content_hash(raw_text)

    if live_hash != content_hash:
        raise StaleHashError(
            message=f"File hash '{live_hash}' differs from provided hash '{content_hash}'.",
            data={"path": path, "expected_hash": content_hash, "actual_hash": live_hash},
        )

    normalized_text = normalize_line_endings(raw_text)
    lines = normalized_text.splitlines()
    total_lines = len(lines)

    if start_line < 1 or start_line > end_line or end_line > total_lines:
        raise InvalidRangeError(
            message=f"Invalid line range [{start_line}, {end_line}] for {total_lines} lines.",
            data={"path": path, "line_range": [start_line, end_line], "total_lines": total_lines},
        )

    before_lines = lines[: start_line - 1]
    norm_new_content = normalize_line_endings(new_content)
    replacement_lines = norm_new_content.splitlines() if norm_new_content else []
    after_lines = lines[end_line:]

    assembled_lines = before_lines + replacement_lines + after_lines
    assembled_content = "\n".join(assembled_lines)
    if raw_text.endswith("\n") or not raw_text:
        assembled_content += "\n"

    diff_preview = _generate_unified_diff(normalized_text, assembled_content, path)

    proposal = _patch_cache.store(
        path=path,
        base_hash=live_hash,
        new_content=assembled_content,
        diff=diff_preview,
    )

    return {
        "status": "ok",
        "patch_id": proposal.patch_id,
        "path": path,
        "diff_preview": diff_preview,
        "expires_in_seconds": proposal.ttl_seconds,
    }


def apply_patch(
    patch_id: str,
    tx_id: str | None = None,
    verify_syntax: bool = True,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Atomically commit a staged patch proposal to disk after CAS re-validation.

    Args:
        patch_id: UUID of the staged patch.
        tx_id: Optional transaction ID (for multi-file transactions).
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

    atomic_write_file(resolved_path, proposal.new_content)
    _patch_cache.mark_applied(patch_id)
    new_hash = compute_content_hash(proposal.new_content)

    return {
        "status": "applied",
        "patch_id": patch_id,
        "path": proposal.path,
        "new_hash": new_hash,
    }


__all__ = [
    "apply_patch",
    "get_file_hash",
    "get_patch_cache",
    "propose_edit",
    "propose_line_edit",
    "read_file",
    "search_code",
]
