"""Unit and scenario tests for multi-file transaction manager and operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.engine import (
    apply_patch,
    begin_transaction,
    commit_transaction,
    propose_edit,
    rollback_transaction,
)
from core.transactions import reset_transaction_manager
from errors import (
    FileModifiedError,
    RollbackTriggeredError,
    TransactionActiveError,
    TransactionNotFoundError,
)


@pytest.fixture(autouse=True)
def clean_transaction_state():
    """Ensure clean transaction state before and after each test."""
    reset_transaction_manager()
    yield
    reset_transaction_manager()


def test_transaction_lifecycle_begin_and_duplicate(temp_git_repo: Path):
    """Verify begin_transaction opens transaction and rejects duplicate active transaction."""
    tx_info = begin_transaction(workspace_root=temp_git_repo)
    assert tx_info["status"] == "open"
    assert "tx_id" in tx_info
    assert tx_info.get("expires_in_seconds", 0) > 0

    # Attempting to open another transaction when one is active should raise
    # TransactionActiveError (-32031)
    with pytest.raises(TransactionActiveError) as exc_info:
        begin_transaction(workspace_root=temp_git_repo)
    assert exc_info.value.code == -32031

    # Cleanup
    rollback_res = rollback_transaction(tx_id=tx_info["tx_id"], workspace_root=temp_git_repo)
    assert rollback_res["status"] == "rolled_back"


def test_transaction_not_found(temp_git_repo: Path):
    """Verify operations with unknown tx_id raise TransactionNotFoundError (-32030)."""
    unknown_tx = "non-existent-tx-id"
    with pytest.raises(TransactionNotFoundError) as exc_commit:
        commit_transaction(tx_id=unknown_tx, workspace_root=temp_git_repo)
    assert exc_commit.value.code == -32030

    with pytest.raises(TransactionNotFoundError) as exc_rollback:
        rollback_transaction(tx_id=unknown_tx, workspace_root=temp_git_repo)
    assert exc_rollback.value.code == -32030


def test_apply_patch_transactional_staging(temp_git_repo: Path):
    """Verify apply_patch with tx_id stages patch without modifying disk."""
    file_a = temp_git_repo / "a.py"
    file_a.write_text("x = 1\n", encoding="utf-8")

    tx = begin_transaction(workspace_root=temp_git_repo)
    tx_id = tx["tx_id"]

    try:
        p1 = propose_edit(
            path="a.py",
            old_str="x = 1",
            new_str="x = 2",
            expected_occurrences=1,
            workspace_root=temp_git_repo,
        )
        stage_res = apply_patch(
            patch_id=p1["patch_id"],
            tx_id=tx_id,
            workspace_root=temp_git_repo,
        )
        assert stage_res["status"] == "staged"
        assert stage_res["patch_id"] == p1["patch_id"]
        assert stage_res["path"] == "a.py"

        # Verify live file on disk is NOT modified yet
        assert file_a.read_text(encoding="utf-8") == "x = 1\n"
    finally:
        rollback_transaction(tx_id=tx_id, workspace_root=temp_git_repo)


def test_apply_patch_staged_with_invalid_tx_id(temp_git_repo: Path):
    """Verify apply_patch with invalid tx_id raises TransactionNotFoundError."""
    file_a = temp_git_repo / "a.py"
    file_a.write_text("x = 1\n", encoding="utf-8")

    p1 = propose_edit(
        path="a.py",
        old_str="x = 1",
        new_str="x = 2",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )
    with pytest.raises(TransactionNotFoundError) as exc:
        apply_patch(
            patch_id=p1["patch_id"],
            tx_id="invalid-tx",
            workspace_root=temp_git_repo,
        )
    assert exc.value.code == -32030


def test_commit_transaction_success(temp_git_repo: Path):
    """Verify commit_transaction atomically writes multi-file modifications."""
    file_a = temp_git_repo / "file_a.py"
    file_b = temp_git_repo / "file_b.py"
    file_a.write_text("val_a = 10\n", encoding="utf-8")
    file_b.write_text("val_b = 20\n", encoding="utf-8")

    tx = begin_transaction(workspace_root=temp_git_repo)
    tx_id = tx["tx_id"]

    p_a = propose_edit(
        path="file_a.py",
        old_str="val_a = 10",
        new_str="val_a = 100",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )
    p_b = propose_edit(
        path="file_b.py",
        old_str="val_b = 20",
        new_str="val_b = 200",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )

    apply_patch(patch_id=p_a["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)
    apply_patch(patch_id=p_b["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)

    # Disk files remain unchanged before commit
    assert file_a.read_text(encoding="utf-8") == "val_a = 10\n"
    assert file_b.read_text(encoding="utf-8") == "val_b = 20\n"

    commit_res = commit_transaction(tx_id=tx_id, workspace_root=temp_git_repo)
    assert commit_res["status"] == "committed"
    assert commit_res["tx_id"] == tx_id
    assert set(commit_res["files_updated"]) == {"file_a.py", "file_b.py"}
    assert "file_hashes" in commit_res

    # Disk files are now atomically updated
    assert file_a.read_text(encoding="utf-8") == "val_a = 100\n"
    assert file_b.read_text(encoding="utf-8") == "val_b = 200\n"


def test_commit_transaction_cas_drift_abort(temp_git_repo: Path):
    """Verify commit_transaction aborts with E_FILE_MODIFIED (-32011) if any file drifts."""
    file_a = temp_git_repo / "drift_a.py"
    file_b = temp_git_repo / "drift_b.py"
    file_a.write_text("orig_a = True\n", encoding="utf-8")
    file_b.write_text("orig_b = True\n", encoding="utf-8")

    tx = begin_transaction(workspace_root=temp_git_repo)
    tx_id = tx["tx_id"]

    try:
        p_a = propose_edit(
            path="drift_a.py",
            old_str="orig_a = True",
            new_str="orig_a = False",
            expected_occurrences=1,
            workspace_root=temp_git_repo,
        )
        p_b = propose_edit(
            path="drift_b.py",
            old_str="orig_b = True",
            new_str="orig_b = False",
            expected_occurrences=1,
            workspace_root=temp_git_repo,
        )
        apply_patch(patch_id=p_a["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)
        apply_patch(patch_id=p_b["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)

        # Simulate concurrent drift on file_b
        file_b.write_text("orig_b = True # external edit\n", encoding="utf-8")

        with pytest.raises(FileModifiedError) as exc_info:
            commit_transaction(tx_id=tx_id, workspace_root=temp_git_repo)
        assert exc_info.value.code == -32011

        # Live files must NOT have had transaction applied
        assert file_a.read_text(encoding="utf-8") == "orig_a = True\n"
        assert file_b.read_text(encoding="utf-8") == "orig_b = True # external edit\n"
    finally:
        rollback_transaction(tx_id=tx_id, workspace_root=temp_git_repo)


def test_commit_transaction_syntax_rollback(temp_git_repo: Path):
    """Verify commit_transaction automatically rolls back all files if syntax check fails."""
    good_file = temp_git_repo / "good.py"
    bad_file = temp_git_repo / "bad.py"
    good_file.write_text("valid = 1\n", encoding="utf-8")
    bad_file.write_text("syntax_ok = True\n", encoding="utf-8")

    tx = begin_transaction(workspace_root=temp_git_repo)
    tx_id = tx["tx_id"]

    p_good = propose_edit(
        path="good.py",
        old_str="valid = 1",
        new_str="valid = 2",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )
    p_bad = propose_edit(
        path="bad.py",
        old_str="syntax_ok = True",
        new_str="def syntax_broken(\n",  # Invalid python syntax
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )
    apply_patch(patch_id=p_good["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)
    apply_patch(patch_id=p_bad["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)

    with pytest.raises(RollbackTriggeredError) as exc_info:
        commit_transaction(tx_id=tx_id, verify_syntax=True, workspace_root=temp_git_repo)
    assert exc_info.value.code == -32042

    # Verify BOTH files rolled back to pre-commit baseline
    assert good_file.read_text(encoding="utf-8") == "valid = 1\n"
    assert bad_file.read_text(encoding="utf-8") == "syntax_ok = True\n"


def test_rollback_transaction_cleanup(temp_git_repo: Path):
    """Verify rollback_transaction purges staging state and preserves live files."""
    file_x = temp_git_repo / "mod.py"
    file_x.write_text("state = 'initial'\n", encoding="utf-8")

    tx = begin_transaction(workspace_root=temp_git_repo)
    tx_id = tx["tx_id"]

    p = propose_edit(
        path="mod.py",
        old_str="state = 'initial'",
        new_str="state = 'updated'",
        expected_occurrences=1,
        workspace_root=temp_git_repo,
    )
    apply_patch(patch_id=p["patch_id"], tx_id=tx_id, workspace_root=temp_git_repo)

    res = rollback_transaction(tx_id=tx_id, workspace_root=temp_git_repo)
    assert res["status"] == "rolled_back"
    assert res["tx_id"] == tx_id
    assert res["discarded_patches_count"] == 1

    # Verify working tree is intact
    assert file_x.read_text(encoding="utf-8") == "state = 'initial'\n"

    # Transaction is closed; committing or rolling back again raises E_TRANSACTION_NOT_FOUND
    with pytest.raises(TransactionNotFoundError):
        commit_transaction(tx_id=tx_id, workspace_root=temp_git_repo)
