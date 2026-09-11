"""Core engine, hashing, and workspace utilities for CEMP."""

from __future__ import annotations

from core.hasher import compute_content_hash, compute_file_hash, normalize_line_endings

__all__ = [
    "compute_content_hash",
    "compute_file_hash",
    "normalize_line_endings",
]
