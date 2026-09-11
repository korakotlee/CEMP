"""SHA-256 CAS content hasher with line ending normalization."""

from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_line_endings(content: str) -> str:
    """Normalize CRLF and standalone CR line endings to LF.

    Args:
        content: Input string with arbitrary line endings.

    Returns:
        String with all line endings converted to Unix LF (`\n`).
    """
    return content.replace("\r\n", "\n").replace("\r", "\n")


def compute_content_hash(content: str) -> str:
    """Compute deterministic SHA-256 digest of normalized text content.

    Args:
        content: Text content to hash.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.
    """
    normalized = normalize_line_endings(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_file_hash(file_path: Path | str) -> str:
    """Read a file from disk and compute its normalized SHA-256 digest.

    Args:
        file_path: Path to the target file.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.
    """
    path = Path(file_path)
    raw_content = path.read_text(encoding="utf-8", errors="replace")
    return compute_content_hash(raw_content)
