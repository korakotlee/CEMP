"""Proposal generation engine for exact-string and line-range edits."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from core.hasher import compute_content_hash, normalize_line_endings
from core.patch_cache import PatchCache
from core.workspace import resolve_workspace_path
from errors import (
    InvalidRangeError,
    NoMatchError,
    OccurrenceMismatchError,
    StaleHashError,
)


def generate_unified_diff(
    original_text: str,
    new_text: str,
    path: str,
) -> str:
    """Generate standard unified diff preview between two texts.

    Args:
        original_text: Baseline text.
        new_text: Updated text.
        path: Path to target file.

    Returns:
        Unified diff string with headers a/path and b/path.
    """
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
    patch_cache: PatchCache,
    expected_occurrences: int = 1,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose an exact string replacement with strict occurrence enforcement.

    Args:
        path: Target file path within workspace.
        old_str: Exact substring to be replaced.
        new_str: Replacement substring.
        patch_cache: PatchCache instance to stage proposal.
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
    diff_preview = generate_unified_diff(normalized_text, new_content, path)

    proposal = patch_cache.store(
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
    patch_cache: PatchCache,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Propose a line-bounded edit protected by CAS hash validation.

    Args:
        path: Target file path within workspace.
        start_line: 1-indexed start line number.
        end_line: 1-indexed inclusive end line number.
        new_content: Replacement text for the specified line block.
        content_hash: SHA-256 hash expected from prior read_file.
        patch_cache: PatchCache instance to stage proposal.
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

    diff_preview = generate_unified_diff(normalized_text, assembled_content, path)

    proposal = patch_cache.store(
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
