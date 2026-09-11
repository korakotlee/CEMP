"""Filesystem, transaction, syntax, and system error classes for CEMP."""

from __future__ import annotations

from typing import Any

from errors.base import CEMPError
from errors.codes import CEMPErrorCode


class TransactionNotFoundError(CEMPError):
    def __init__(
        self,
        message: str = "Transaction ID does not correspond to an open transaction.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_TRANSACTION_NOT_FOUND,
            "E_TRANSACTION_NOT_FOUND",
            message,
            data,
            True,
            "BEGIN_TRANSACTION",
        )


class TransactionActiveError(CEMPError):
    def __init__(
        self,
        message: str = "A transaction is already active on this session.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_TRANSACTION_ACTIVE,
            "E_TRANSACTION_ACTIVE",
            message,
            data,
            True,
            "COMMIT_OR_ROLLBACK_EXISTING",
        )


class TransactionConflictError(CEMPError):
    def __init__(
        self,
        message: str = "Transaction targets files currently locked or conflicting.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_TRANSACTION_CONFLICT,
            "E_TRANSACTION_CONFLICT",
            message,
            data,
            True,
            "ABORT_AND_RETRY",
        )


class SyntaxErrorCEMP(CEMPError):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(
            CEMPErrorCode.E_SYNTAX_ERROR,
            "E_SYNTAX_ERROR",
            message,
            data,
            True,
            "FIX_SYNTAX_AND_RETRY",
        )


class TestsFailedError(CEMPError):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(
            CEMPErrorCode.E_TESTS_FAILED,
            "E_TESTS_FAILED",
            message,
            data,
            True,
            "INSPECT_TEST_OUTPUT",
        )


class RollbackTriggeredError(CEMPError):
    def __init__(self, message: str, data: dict[str, Any] | None = None):
        super().__init__(
            CEMPErrorCode.E_ROLLBACK_TRIGGERED,
            "E_ROLLBACK_TRIGGERED",
            message,
            data,
            True,
            "INSPECT_ERRORS",
        )


class PathTraversalError(CEMPError):
    def __init__(
        self,
        message: str = "Path attempts traversal outside permissible workspace roots.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_PATH_TRAVERSAL,
            "E_PATH_TRAVERSAL",
            message,
            data,
            False,
            "RESTRICT_TO_WORKSPACE",
        )


class FileNotFoundCEMPError(CEMPError):
    def __init__(
        self,
        message: str = "File does not exist on filesystem.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_FILE_NOT_FOUND, "E_FILE_NOT_FOUND", message, data, True, "CHECK_PATH"
        )


class PermissionDeniedError(CEMPError):
    def __init__(
        self,
        message: str = "Insufficient filesystem read or write permissions.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_PERMISSION_DENIED,
            "E_PERMISSION_DENIED",
            message,
            data,
            False,
            "CHECK_PERMISSIONS",
        )


# Aliases for naming flexibility
FileNotFoundCempError = FileNotFoundCEMPError
PermissionDeniedCempError = PermissionDeniedError


class IsDirectoryError(CEMPError):
    def __init__(
        self,
        message: str = "Expected regular file, but path points to a directory.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_IS_DIRECTORY, "E_IS_DIRECTORY", message, data, False, "CHECK_PATH"
        )


class UndoUnavailableError(CEMPError):
    def __init__(
        self,
        message: str = "No previous patch or git history available to undo.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_UNDO_UNAVAILABLE,
            "E_UNDO_UNAVAILABLE",
            message,
            data,
            False,
            "NO_ACTION",
        )


class GitDirtyConflictError(CEMPError):
    def __init__(
        self,
        message: str = "Working tree has unstaged modifications conflicting with undo.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_GIT_DIRTY_CONFLICT,
            "E_GIT_DIRTY_CONFLICT",
            message,
            data,
            True,
            "STASH_OR_COMMIT",
        )


class InternalServerError(CEMPError):
    def __init__(
        self,
        message: str = "Internal server error occurred.",
        data: dict[str, Any] | None = None,
    ):
        super().__init__(
            CEMPErrorCode.E_INTERNAL_ERROR,
            "E_INTERNAL_ERROR",
            message,
            data,
            False,
            "INSPECT_LOGS",
        )
