"""Deterministic inspection engine for reading files, computing CAS hashes, and searching code."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.hasher import compute_content_hash, normalize_line_endings
from core.workspace import get_default_workspace_root, resolve_workspace_path
from errors import InvalidRangeError

MAX_SEARCH_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10MB


def read_file(
    path: str,
    line_range: list[int] | None = None,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Read file content with 1-indexed line numbers and content SHA-256 hash.

    Args:
        path: Path to target file within workspace.
        line_range: Optional [start_line, end_line] 1-indexed inclusive range.
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/read_file.json.

    Raises:
        InvalidRangeError: If line_range is inverted, non-positive, or out of bounds.
        PathTraversalError: If path escapes workspace.
        FileNotFoundCEMPError: If path does not exist.
        IsDirectoryError: If path is a directory.
    """
    resolved_path = resolve_workspace_path(path, workspace_root=workspace_root, must_exist=True)
    raw_text = resolved_path.read_text(encoding="utf-8", errors="replace")
    normalized_text = normalize_line_endings(raw_text)
    content_hash = compute_content_hash(raw_text)

    all_lines = normalized_text.splitlines() if normalized_text else []
    total_lines = len(all_lines)

    if line_range is not None:
        start_line, end_line = line_range[0], line_range[1]
        if start_line < 1 or start_line > end_line or end_line > total_lines:
            raise InvalidRangeError(
                message=(
                    f"Invalid line range [{start_line}, {end_line}] "
                    f"for file with {total_lines} total lines."
                ),
                data={
                    "path": path,
                    "line_range": line_range,
                    "total_lines": total_lines,
                },
            )
        selected_lines = [
            [idx, all_lines[idx - 1]] for idx in range(start_line, end_line + 1)
        ]
    else:
        selected_lines = [
            [idx + 1, line_text] for idx, line_text in enumerate(all_lines)
        ]

    return {
        "path": path,
        "lines": selected_lines,
        "content_hash": content_hash,
        "total_lines": total_lines,
    }


def get_file_hash(
    path: str,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Retrieve the optimistic SHA-256 CAS content hash for a file.

    Args:
        path: Path to target file within workspace.
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary containing path and hex-encoded SHA-256 content_hash.
    """
    resolved_path = resolve_workspace_path(path, workspace_root=workspace_root, must_exist=True)
    raw_text = resolved_path.read_text(encoding="utf-8", errors="replace")
    content_hash = compute_content_hash(raw_text)

    return {
        "path": path,
        "content_hash": content_hash,
    }


def search_code(
    pattern: str,
    path_glob: str = "**/*",
    regex: bool = False,
    context_lines: int = 3,
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """Search for literal text or regex patterns across workspace files.

    Args:
        pattern: Literal string or regex pattern to search.
        path_glob: Glob pattern filtering target files.
        regex: Whether to treat pattern as regular expression.
        context_lines: Number of surrounding context lines (0 to 20).
        workspace_root: Optional workspace root directory.

    Returns:
        Dictionary conforming to protocol/schemas/search_code.json.
    """
    root = (Path(workspace_root) if workspace_root else get_default_workspace_root()).resolve()
    context_lines = max(0, min(20, context_lines))

    compiled_regex: re.Pattern[str] | None = None
    if regex:
        compiled_regex = re.compile(pattern)

    matches: list[dict[str, Any]] = []

    # Find matching candidate files using glob resolution
    if "/" not in path_glob and not path_glob.startswith("**"):
        candidates = sorted(list(set(root.glob(path_glob)).union(root.glob(f"**/{path_glob}"))))
    else:
        candidates = sorted(list(root.glob(path_glob)))

    for item in candidates:
        if not item.is_file():
            continue

        # Skip protected internal directories and files
        if any(part.startswith(".git") for part in item.parts):
            continue
        if item.name == ".env" or item.name.startswith(".env."):
            continue

        rel_path = item.relative_to(root).as_posix()

        # Check file size limit
        try:
            if item.stat().st_size > MAX_SEARCH_FILE_SIZE_BYTES:
                continue
            raw_text = item.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError):
            continue

        lines = normalize_line_endings(raw_text).splitlines()
        for idx, line in enumerate(lines):
            is_match = False
            if compiled_regex:
                if compiled_regex.search(line):
                    is_match = True
            elif pattern in line:
                is_match = True

            if is_match:
                start_before = max(0, idx - context_lines)
                end_after = min(len(lines), idx + 1 + context_lines)
                matches.append(
                    {
                        "file": rel_path,
                        "line": idx + 1,
                        "match_content": line,
                        "context_before": lines[start_before:idx],
                        "context_after": lines[idx + 1:end_after],
                    }
                )

    return {
        "total_matches": len(matches),
        "matches": matches,
    }
