"""Unit tests for SHA-256 CAS hasher and line ending normalization."""

from __future__ import annotations

from pathlib import Path

from core.hasher import compute_content_hash, compute_file_hash, normalize_line_endings


def test_normalize_line_endings():
    """Verify that CRLF and CR line endings are normalized to LF."""
    assert normalize_line_endings("line1\r\nline2\r\n") == "line1\nline2\n"
    assert normalize_line_endings("line1\rline2\r") == "line1\nline2\n"
    assert normalize_line_endings("line1\nline2\n") == "line1\nline2\n"
    assert normalize_line_endings("mixed\r\nendings\rhere\n") == "mixed\nendings\nhere\n"


def test_compute_content_hash_known_vectors():
    """Verify content hash against known SHA-256 test vectors."""
    # Empty string hash
    empty_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert compute_content_hash("") == empty_hash

    # "hello\n" hash
    expected_hello_hash = "5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03"
    assert compute_content_hash("hello\n") == expected_hello_hash


def test_compute_content_hash_crlf_lf_invariance():
    """Verify that hashing content with CRLF vs LF yields identical digests."""
    crlf_content = "def add(a, b):\r\n    return a + b\r\n"
    lf_content = "def add(a, b):\n    return a + b\n"
    assert compute_content_hash(crlf_content) == compute_content_hash(lf_content)


def test_compute_file_hash(tmp_path: Path):
    """Verify compute_file_hash on disk files with CRLF endings."""
    sample_file = tmp_path / "sample.py"
    sample_file.write_bytes(b"x = 1\r\ny = 2\r\n")

    expected_hash = compute_content_hash("x = 1\ny = 2\n")
    assert compute_file_hash(sample_file) == expected_hash
