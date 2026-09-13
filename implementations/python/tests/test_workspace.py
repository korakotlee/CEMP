"""Unit tests for workspace path resolution and security boundary validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.workspace import resolve_workspace_path
from errors import (
    FileNotFoundCEMPError,
    IsDirectoryError,
    PathTraversalError,
    PermissionDeniedError,
)


def test_resolve_valid_relative_path(tmp_path: Path):
    """Verify resolution of valid relative paths within workspace."""
    test_file = tmp_path / "src" / "main.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("print('hello')", encoding="utf-8")

    resolved = resolve_workspace_path("src/main.py", workspace_root=tmp_path)
    assert resolved == test_file.resolve()


def test_resolve_valid_absolute_path(tmp_path: Path):
    """Verify resolution of valid absolute paths within workspace."""
    test_file = tmp_path / "data.txt"
    test_file.write_text("content", encoding="utf-8")

    resolved = resolve_workspace_path(str(test_file), workspace_root=tmp_path)
    assert resolved == test_file.resolve()


def test_reject_path_traversal(tmp_path: Path):
    """Verify rejection of directory traversal attempts escaping workspace root."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret", encoding="utf-8")

    with pytest.raises(PathTraversalError) as exc_info:
        resolve_workspace_path("../secret.txt", workspace_root=workspace)

    assert exc_info.value.code == -32050
    assert exc_info.value.recoverable is False


def test_reject_git_directory_access(tmp_path: Path):
    """Verify rejection of paths attempting to inspect internal .git directory."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    config_file = git_dir / "config"
    config_file.write_text("[core]", encoding="utf-8")

    with pytest.raises(PermissionDeniedError) as exc_info:
        resolve_workspace_path(".git/config", workspace_root=tmp_path)

    assert exc_info.value.code == -32052


def test_reject_sensitive_env_file_access(tmp_path: Path):
    """Verify rejection of paths targeting sensitive .env credentials files."""
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=12345", encoding="utf-8")

    with pytest.raises(PermissionDeniedError) as exc_info:
        resolve_workspace_path(".env", workspace_root=tmp_path)

    assert exc_info.value.code == -32052


def test_file_not_found(tmp_path: Path):
    """Verify raising of FileNotFoundCEMPError for non-existent paths."""
    with pytest.raises(FileNotFoundCEMPError) as exc_info:
        resolve_workspace_path("non_existent.py", workspace_root=tmp_path, must_exist=True)

    assert exc_info.value.code == -32051
    assert exc_info.value.recoverable is True


def test_reject_directory_when_file_expected(tmp_path: Path):
    """Verify raising IsDirectoryError when a directory path is inspected as a file."""
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()

    with pytest.raises(IsDirectoryError) as exc_info:
        resolve_workspace_path("subdir", workspace_root=tmp_path, allow_directory=False)

    assert exc_info.value.code == -32053


def test_find_git_root_and_default_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify git root traversal locates repo root and get_default_workspace_root honors it."""
    from core.workspace import find_git_root, get_default_workspace_root

    repo_root = tmp_path / "my_repo"
    sub_dir = repo_root / "implementations" / "python"
    sub_dir.mkdir(parents=True)
    git_dir = repo_root / ".git"
    git_dir.mkdir()

    # When start_path is in sub_dir, it should find repo_root
    assert find_git_root(sub_dir) == repo_root

    # When env var is unset and cwd is sub_dir
    monkeypatch.delenv("CEMP_WORKSPACE_ROOT", raising=False)
    monkeypatch.chdir(sub_dir)
    assert get_default_workspace_root() == repo_root

    # When env var is explicitly set, env var takes precedence
    override_dir = tmp_path / "custom_root"
    override_dir.mkdir()
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(override_dir))
    assert get_default_workspace_root() == override_dir.resolve()
