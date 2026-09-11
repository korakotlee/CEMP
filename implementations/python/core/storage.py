"""Atomic file replacement with sibling temporary files and filesystem synchronization."""

from __future__ import annotations

import os
import uuid
from pathlib import Path


def atomic_write_file(path: Path | str, content: str, encoding: str = "utf-8") -> None:
    """Atomically write text content to a target file.

    Uses sibling temporary files and os.replace to ensure atomic updates
    across APFS and POSIX filesystems without corrupting target files on failure.

    Args:
        path: Destination file path.
        content: Text content to write.
        encoding: Text encoding (defaults to utf-8).

    Raises:
        OSError: If writing, syncing, or replacing fails.
    """
    target = Path(path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)

    # Generate sibling temporary file in the same directory (required for atomic rename)
    tmp_path = target.parent / f"{target.name}.{uuid.uuid4().hex}.cemp.tmp"

    try:
        with open(tmp_path, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, target)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
