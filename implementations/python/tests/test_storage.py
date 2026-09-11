"""Unit tests for atomic file replacement in core/storage.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from core.storage import atomic_write_file


def test_atomic_write_success(tmp_path: Path):
    """Verify atomic write updates file content and does not leave temporary files."""
    target = tmp_path / "sample.py"
    target.write_text("initial content", encoding="utf-8")

    atomic_write_file(target, "new content")

    assert target.read_text(encoding="utf-8") == "new content"
    # Ensure no lingering .cemp.tmp files
    tmp_files = list(tmp_path.glob("*.cemp.tmp"))
    assert len(tmp_files) == 0


def test_atomic_write_new_file(tmp_path: Path):
    """Verify atomic write works for creating a brand new file."""
    target = tmp_path / "new_dir" / "created.py"
    target.parent.mkdir(parents=True, exist_ok=True)

    atomic_write_file(target, "print('created')")

    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "print('created')"


def test_atomic_write_cleanup_on_error(tmp_path: Path):
    """Verify sibling temporary file is unlinked if write fails and original file is preserved."""
    target = tmp_path / "preserved.py"
    target.write_text("original content", encoding="utf-8")

    with patch("os.fsync", side_effect=OSError("Simulated disk fsync failure")):
        with pytest.raises(OSError, match="Simulated disk fsync failure"):
            atomic_write_file(target, "should not be saved")

    # Original content preserved
    assert target.read_text(encoding="utf-8") == "original content"
    # No temporary file left behind
    tmp_files = list(tmp_path.glob("*.cemp.tmp"))
    assert len(tmp_files) == 0
