"""Proposal, patch, and matching exceptions for CEMP."""

from __future__ import annotations

from typing import Any

from errors.base import CEMPError
from errors.codes import CEMPErrorCode


class NoMatchError(CEMPError):
    def __init__(
        self,
        message: str = "Target string or line range was not found in target file.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(CEMPErrorCode.E_NO_MATCH, "E_NO_MATCH", message, data, True, "RE_INSPECT")


class OccurrenceMismatchError(CEMPError):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(
            CEMPErrorCode.E_OCCURRENCE_MISMATCH,
            "E_OCCURRENCE_MISMATCH",
            message,
            data,
            True,
            "EXPAND_CONTEXT",
        )


class AmbiguousMatchError(CEMPError):
    def __init__(
        self,
        message: str = "Target string is ambiguous across target scope.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_AMBIGUOUS_MATCH,
            "E_AMBIGUOUS_MATCH",
            message,
            data,
            True,
            "EXPAND_CONTEXT",
        )


class InvalidRangeError(CEMPError):
    def __init__(
        self,
        message: str = "Specified line numbers are invalid or out of bounds.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_INVALID_RANGE, "E_INVALID_RANGE", message, data, True, "RE_INSPECT"
        )


class StaleHashError(CEMPError):
    def __init__(
        self,
        message: str = "File content hash differs from provided content_hash.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_STALE_HASH, "E_STALE_HASH", message, data, True, "RE_READ_AND_REBASE"
        )


class FileModifiedError(CEMPError):
    def __init__(
        self,
        message: str = "File was modified on disk while patch was pending.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_FILE_MODIFIED,
            "E_FILE_MODIFIED",
            message,
            data,
            True,
            "RE_READ_AND_REBASE",
        )


class PatchNotFoundError(CEMPError):
    def __init__(
        self,
        message: str = "Patch ID was not found in staging memory.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_PATCH_NOT_FOUND, "E_PATCH_NOT_FOUND", message, data, True, "RE_PROPOSE"
        )


class PatchExpiredError(CEMPError):
    def __init__(
        self,
        message: str = "Patch ID has expired from memory cache.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_PATCH_EXPIRED, "E_PATCH_EXPIRED", message, data, True, "RE_PROPOSE"
        )


class PatchAlreadyAppliedError(CEMPError):
    def __init__(
        self,
        message: str = "Patch ID was already committed to disk.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_PATCH_ALREADY_APPLIED,
            "E_PATCH_ALREADY_APPLIED",
            message,
            data,
            False,
            "NO_ACTION",
        )
