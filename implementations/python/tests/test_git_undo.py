"""Tests for GitUndoManager (zero-pollution Git-backed undo mechanics)."""

import subprocess
from pathlib import Path

import pytest

from core.git_undo import GitUndoManager
from errors import CEMPError, CEMPErrorCode


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with initial commit."""
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test Agent"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "agent@cemp.spec"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    test_file = tmp_path / "sample.py"
    test_file.write_text("print('version 1')\n", encoding="utf-8")
    subprocess.run(["git", "add", "sample.py"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path


def test_git_snapshot_and_zero_pollution(git_repo: Path):
    """Snapshot should create a loose blob without polluting commits, index, or reflog."""
    target_file = git_repo / "sample.py"
    manager = GitUndoManager(workspace_root=git_repo)

    # Get initial git state
    commit_count_before = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    reflog_before = subprocess.run(
        ["git", "reflog"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Capture pre-edit snapshot
    snapshot = manager.snapshot(target_file)
    assert snapshot.is_git is True
    assert snapshot.blob_id is not None
    assert len(snapshot.blob_id) == 40

    # Overwrite file with new content
    target_file.write_text("print('version 2')\n", encoding="utf-8")

    # Verify no commits or reflog entries were created by snapshot
    commit_count_after = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    reflog_after = subprocess.run(
        ["git", "reflog"],
        cwd=git_repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    assert commit_count_after == commit_count_before
    assert reflog_after == reflog_before

    # Rollback should restore version 1
    manager.rollback(snapshot)
    assert target_file.read_text(encoding="utf-8") == "print('version 1')\n"


def test_non_git_fallback_snapshot(tmp_path: Path):
    """Snapshot and rollback in non-git workspace should use in-memory/disk fallback."""
    non_git_dir = tmp_path / "no_git"
    non_git_dir.mkdir()
    target_file = non_git_dir / "plain.txt"
    target_file.write_text("initial content\n", encoding="utf-8")

    manager = GitUndoManager(workspace_root=non_git_dir)
    snapshot = manager.snapshot(target_file)
    assert snapshot.is_git is False
    assert snapshot.content_bytes == b"initial content\n"

    # Modify file
    target_file.write_text("modified content\n", encoding="utf-8")

    # Rollback
    manager.rollback(snapshot)
    assert target_file.read_text(encoding="utf-8") == "initial content\n"


def test_undo_last_lifo_stack(git_repo: Path):
    """undo_last should revert patches in LIFO order and support path filtering."""
    target_file = git_repo / "sample.py"
    manager = GitUndoManager(workspace_root=git_repo)

    # Patch 1
    snap1 = manager.snapshot(target_file)
    target_file.write_text("print('version 2')\n", encoding="utf-8")
    manager.record_applied(patch_id="patch-1", target_path=str(target_file), snapshot=snap1)

    # Patch 2
    snap2 = manager.snapshot(target_file)
    target_file.write_text("print('version 3')\n", encoding="utf-8")
    manager.record_applied(patch_id="patch-2", target_path=str(target_file), snapshot=snap2)

    # Undo Patch 2
    res2 = manager.undo_last()
    assert res2.status == "reverted"
    assert res2.reverted_patch_id == "patch-2"
    assert target_file.read_text(encoding="utf-8") == "print('version 2')\n"

    # Undo Patch 1
    res1 = manager.undo_last(target_path=str(target_file))
    assert res1.status == "reverted"
    assert res1.reverted_patch_id == "patch-1"
    assert target_file.read_text(encoding="utf-8") == "print('version 1')\n"

    # Empty stack should raise E_UNDO_UNAVAILABLE
    with pytest.raises(CEMPError) as exc_info:
        manager.undo_last()
    assert exc_info.value.code == CEMPErrorCode.E_UNDO_UNAVAILABLE.value

