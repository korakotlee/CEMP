"""Unit and scenario tests for two-phase commit editing engine and server tools."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from core.engine import (
    apply_patch,
    get_patch_cache,
    propose_edit,
    propose_line_edit,
    read_file,
)
from errors import (
    FileModifiedError,
    InvalidRangeError,
    NoMatchError,
    OccurrenceMismatchError,
    PatchAlreadyAppliedError,
    PatchExpiredError,
    StaleHashError,
)


def test_propose_edit_success(temp_git_repo: Path):
    """Verify propose_edit returns patch_id and unified diff without modifying file on disk."""
    target_file = temp_git_repo / "main.py"
    target_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    result = propose_edit(
        path="main.py",
        old_str="return 'world'",
        new_str="return 'cemp'",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )

    assert result["status"] == "ok"
    assert "patch_id" in result
    assert result["match_count"] == 1
    assert "--- a/main.py" in result["diff_preview"]
    assert "+++ b/main.py" in result["diff_preview"]
    assert "-    return 'world'" in result["diff_preview"]
    assert "+    return 'cemp'" in result["diff_preview"]

    # File on disk should remain untouched
    assert target_file.read_text(encoding="utf-8") == "def hello():\n    return 'world'\n"


def test_propose_edit_no_match(temp_git_repo: Path):
    """Verify propose_edit raises NoMatchError (-32000) when old_str is absent."""
    target_file = temp_git_repo / "main.py"
    target_file.write_text("alpha = 1\n", encoding="utf-8")

    with pytest.raises(NoMatchError) as exc_info:
        propose_edit(
            path="main.py",
            old_str="beta = 2",
            new_str="gamma = 3",
            workspace_root=temp_git_repo,
        )
    assert exc_info.value.code == -32000
    assert exc_info.value.recoverable is True


def test_propose_edit_occurrence_mismatch(temp_git_repo: Path):
    """Verify propose_edit raises OccurrenceMismatchError (-32001) with match locations."""
    target_file = temp_git_repo / "main.py"
    content = "item = 10\nitem = 20\nitem = 30\n"
    target_file.write_text(content, encoding="utf-8")

    with pytest.raises(OccurrenceMismatchError) as exc_info:
        propose_edit(
            path="main.py",
            old_str="item = ",
            new_str="value = ",
            expected_occurrences=1,
            workspace_root=temp_git_repo,
        )
    assert exc_info.value.code == -32001
    assert exc_info.value.data["actual_occurrences"] == 3
    assert len(exc_info.value.data["matches"]) == 3


def test_propose_line_edit_success(temp_git_repo: Path):
    """Verify propose_line_edit validates content_hash and line range."""
    target_file = temp_git_repo / "calc.py"
    target_file.write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")

    inspection = read_file("calc.py", workspace_root=temp_git_repo)
    content_hash = inspection["content_hash"]

    result = propose_line_edit(
        path="calc.py",
        start_line=2,
        end_line=3,
        new_content="line_two_replaced\nline_three_replaced",
        content_hash=content_hash,
        workspace_root=temp_git_repo,
    )

    assert result["status"] == "ok"
    assert "patch_id" in result
    assert "-line2" in result["diff_preview"]
    assert "+line_two_replaced" in result["diff_preview"]


def test_propose_line_edit_stale_hash(temp_git_repo: Path):
    """Verify propose_line_edit raises StaleHashError (-32010) on CAS hash mismatch."""
    target_file = temp_git_repo / "calc.py"
    target_file.write_text("content\n", encoding="utf-8")

    with pytest.raises(StaleHashError) as exc_info:
        propose_line_edit(
            path="calc.py",
            start_line=1,
            end_line=1,
            new_content="new",
            content_hash="f" * 64,
            workspace_root=temp_git_repo,
        )
    assert exc_info.value.code == -32010


def test_propose_line_edit_invalid_range(temp_git_repo: Path):
    """Verify propose_line_edit raises InvalidRangeError (-32003) on out-of-bounds lines."""
    target_file = temp_git_repo / "calc.py"
    target_file.write_text("single line\n", encoding="utf-8")
    inspection = read_file("calc.py", workspace_root=temp_git_repo)

    with pytest.raises(InvalidRangeError) as exc_info:
        propose_line_edit(
            path="calc.py",
            start_line=2,
            end_line=5,
            new_content="replacement",
            content_hash=inspection["content_hash"],
            workspace_root=temp_git_repo,
        )
    assert exc_info.value.code == -32003


def test_apply_patch_success(temp_git_repo: Path):
    """Verify apply_patch atomically updates the file on disk and marks patch applied."""
    target_file = temp_git_repo / "run.py"
    target_file.write_text("initial = 'value'\n", encoding="utf-8")

    proposal = propose_edit(
        path="run.py",
        old_str="initial = 'value'",
        new_str="initial = 'updated'",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    result = apply_patch(patch_id=patch_id, workspace_root=temp_git_repo)
    assert result["status"] == "applied"
    assert result["patch_id"] == patch_id
    assert target_file.read_text(encoding="utf-8") == "initial = 'updated'\n"

    # Re-applying must raise PatchAlreadyAppliedError (-32022)
    with pytest.raises(PatchAlreadyAppliedError) as exc_info:
        apply_patch(patch_id=patch_id, workspace_root=temp_git_repo)
    assert exc_info.value.code == -32022


def test_apply_patch_collision_file_modified(temp_git_repo: Path):
    """Verify apply_patch detects intervening file modifications on disk and aborts write."""
    target_file = temp_git_repo / "collab.py"
    target_file.write_text("original text\n", encoding="utf-8")

    proposal = propose_edit(
        path="collab.py",
        old_str="original",
        new_str="modified",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    # Simulate concurrent external change on disk
    target_file.write_text("concurrent external edit\n", encoding="utf-8")

    with pytest.raises(FileModifiedError) as exc_info:
        apply_patch(patch_id=patch_id, workspace_root=temp_git_repo)
    assert exc_info.value.code == -32011

    # File must keep the concurrent external edit
    assert target_file.read_text(encoding="utf-8") == "concurrent external edit\n"


def test_apply_patch_expired(temp_git_repo: Path):
    """Verify apply_patch rejects expired proposals with PatchExpiredError (-32021)."""
    target_file = temp_git_repo / "expire.py"
    target_file.write_text("expire test\n", encoding="utf-8")

    proposal = propose_edit(
        path="expire.py",
        old_str="expire test",
        new_str="expired",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    # Expire patch manually in cache
    cache = get_patch_cache()
    p = cache.get(patch_id)
    p.created_at = time.time() - 1000

    with pytest.raises(PatchExpiredError) as exc_info:
        apply_patch(patch_id=patch_id, workspace_root=temp_git_repo)
    assert exc_info.value.code == -32021


def test_apply_patch_syntax_verification_success(temp_git_repo: Path):
    """Verify apply_patch runs syntax verification and reports passed status."""
    target_file = temp_git_repo / "valid_code.py"
    target_file.write_text("value = 1\n", encoding="utf-8")

    proposal = propose_edit(
        path="valid_code.py",
        old_str="value = 1",
        new_str="value = 42",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    result = apply_patch(patch_id=patch_id, verify_syntax=True, workspace_root=temp_git_repo)
    assert result["status"] == "applied"
    assert result["syntax_check"]["passed"] is True
    assert result["syntax_check"]["checker"] == "py_compile"
    assert target_file.read_text(encoding="utf-8") == "value = 42\n"


def test_apply_patch_syntax_failure_auto_rollback(temp_git_repo: Path):
    """Verify apply_patch automatically rolls back file and raises error when syntax is invalid."""
    target_file = temp_git_repo / "rollback_test.py"
    target_file.write_text("x = 10\n", encoding="utf-8")

    proposal = propose_edit(
        path="rollback_test.py",
        old_str="x = 10",
        new_str="def broken(\n",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    with pytest.raises(Exception) as exc_info:
        apply_patch(patch_id=patch_id, verify_syntax=True, workspace_root=temp_git_repo)

    # Must raise E_SYNTAX_ERROR (-32040) or E_ROLLBACK_TRIGGERED (-32042)
    assert getattr(exc_info.value, "code", None) in (-32040, -32042)
    # Target file on disk MUST have been rolled back to initial state
    assert target_file.read_text(encoding="utf-8") == "x = 10\n"


def test_apply_patch_skip_syntax_verification(temp_git_repo: Path):
    """Verify verify_syntax=False writes file without invoking syntax validation."""
    target_file = temp_git_repo / "skip_test.py"
    target_file.write_text("x = 10\n", encoding="utf-8")

    proposal = propose_edit(
        path="skip_test.py",
        old_str="x = 10\n",
        new_str="def broken(\n",
        workspace_root=temp_git_repo,
    )
    patch_id = proposal["patch_id"]

    result = apply_patch(patch_id=patch_id, verify_syntax=False, workspace_root=temp_git_repo)
    assert result["status"] == "applied"
    assert target_file.read_text(encoding="utf-8") == "def broken(\n"


