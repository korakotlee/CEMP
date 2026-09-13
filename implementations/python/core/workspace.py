"""Workspace path resolution and security boundary validation."""

from __future__ import annotations

import os
from pathlib import Path

from errors import (
    FileNotFoundCEMPError,
    IsDirectoryError,
    PathTraversalError,
    PermissionDeniedError,
)

# Protected directories and file patterns
_PROTECTED_DIR_PARTS = {".git"}
_PROTECTED_FILE_PREFIXES = {".env"}


def find_git_root(start_path: Path | None = None) -> Path | None:
    """Traverse upwards from start_path to locate the enclosing git repository root."""
    current = (start_path or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def get_default_workspace_root() -> Path:
    """Retrieve the designated workspace root directory."""
    env_root = os.getenv("CEMP_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root).resolve()
    git_root = find_git_root()
    if git_root is not None:
        return git_root
    return Path.cwd().resolve()


def resolve_workspace_path(
    path: str | Path,
    workspace_root: str | Path | None = None,
    allow_directory: bool = False,
    must_exist: bool = True,
) -> Path:
    """Resolve a path securely within the workspace boundary.

    Args:
        path: Path string or Path object, relative or absolute.
        workspace_root: Optional workspace root directory. Defaults to current workspace.
        allow_directory: Whether directory paths are accepted.
        must_exist: Whether the target path must exist on disk.

    Returns:
        Canonical resolved Path object guaranteed to reside within workspace_root.

    Raises:
        PathTraversalError: If path resolves outside workspace boundary.
        PermissionDeniedError: If path targets protected internal metadata or credentials.
        FileNotFoundCEMPError: If path does not exist and must_exist is True.
        IsDirectoryError: If path is a directory and allow_directory is False.
    """
    root = (Path(workspace_root) if workspace_root else get_default_workspace_root()).resolve()
    raw_path = Path(path)

    # Resolve candidate path against workspace root if relative
    if raw_path.is_absolute():
        resolved = raw_path.resolve()
    else:
        resolved = (root / raw_path).resolve()

    # Enforce workspace root containment
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PathTraversalError(
            message=f"Path '{path}' resolves outside workspace root '{root}'.",
            data={"path": str(path), "workspace_root": str(root)},
        ) from exc

    # Enforce protected internal directories and credential file restriction
    parts_set = set(resolved.parts)
    if _PROTECTED_DIR_PARTS.intersection(parts_set):
        raise PermissionDeniedError(
            message=f"Access to protected repository directory in '{path}' is denied.",
            data={"path": str(path)},
        )

    for prefix in _PROTECTED_FILE_PREFIXES:
        if resolved.name == prefix or resolved.name.startswith(f"{prefix}."):
            raise PermissionDeniedError(
                message=f"Access to sensitive file '{resolved.name}' is denied.",
                data={"path": str(path), "filename": resolved.name},
            )

    # Check filesystem existence if required
    if must_exist and not resolved.exists():
        raise FileNotFoundCEMPError(
            message=f"File '{path}' does not exist on filesystem.",
            data={"path": str(path), "resolved_path": str(resolved)},
        )

    # Check directory constraint
    if not allow_directory and resolved.exists() and resolved.is_dir():
        raise IsDirectoryError(
            message=f"Expected a regular file, but path '{path}' points to a directory.",
            data={"path": str(path), "resolved_path": str(resolved)},
        )

    return resolved
