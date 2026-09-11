"""CEMP Error package exposing standard codes, base models, and exceptions."""

from __future__ import annotations

from errors.base import CEMPError, CEMPErrorPayload, format_cemp_error
from errors.codes import CEMPErrorCode
from errors.proposal_errors import (
    AmbiguousMatchError,
    FileModifiedError,
    InvalidRangeError,
    NoMatchError,
    OccurrenceMismatchError,
    PatchAlreadyAppliedError,
    PatchExpiredError,
    PatchNotFoundError,
    StaleHashError,
)
from errors.system_errors import (
    FileNotFoundCEMPError,
    GitDirtyConflictError,
    InternalServerError,
    IsDirectoryError,
    PathTraversalError,
    PermissionDeniedError,
    RollbackTriggeredError,
    SyntaxErrorCEMP,
    TestsFailedError,
    TransactionActiveError,
    TransactionConflictError,
    TransactionNotFoundError,
    UndoUnavailableError,
)

__all__ = [
    "AmbiguousMatchError",
    "CEMPError",
    "CEMPErrorCode",
    "CEMPErrorPayload",
    "FileModifiedError",
    "FileNotFoundCEMPError",
    "GitDirtyConflictError",
    "InternalServerError",
    "InvalidRangeError",
    "IsDirectoryError",
    "NoMatchError",
    "OccurrenceMismatchError",
    "PatchAlreadyAppliedError",
    "PatchExpiredError",
    "PatchNotFoundError",
    "PathTraversalError",
    "PermissionDeniedError",
    "RollbackTriggeredError",
    "StaleHashError",
    "SyntaxErrorCEMP",
    "TestsFailedError",
    "TransactionActiveError",
    "TransactionConflictError",
    "TransactionNotFoundError",
    "UndoUnavailableError",
    "format_cemp_error",
]
