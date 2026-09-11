"""Standardized CEMP error codes conforming to protocol/error-codes.md."""

from __future__ import annotations

from enum import IntEnum


class CEMPErrorCode(IntEnum):
    """Standardized error codes conforming to protocol/error-codes.md."""

    E_NO_MATCH = -32000
    E_OCCURRENCE_MISMATCH = -32001
    E_AMBIGUOUS_MATCH = -32002
    E_INVALID_RANGE = -32003
    E_STALE_HASH = -32010
    E_FILE_MODIFIED = -32011
    E_PATCH_NOT_FOUND = -32020
    E_PATCH_EXPIRED = -32021
    E_PATCH_ALREADY_APPLIED = -32022
    E_TRANSACTION_NOT_FOUND = -32030
    E_TRANSACTION_ACTIVE = -32031
    E_TRANSACTION_CONFLICT = -32032
    E_SYNTAX_ERROR = -32040
    E_TESTS_FAILED = -32041
    E_ROLLBACK_TRIGGERED = -32042
    E_PATH_TRAVERSAL = -32050
    E_FILE_NOT_FOUND = -32051
    E_PERMISSION_DENIED = -32052
    E_IS_DIRECTORY = -32053
    E_UNDO_UNAVAILABLE = -32060
    E_GIT_DIRTY_CONFLICT = -32061
    E_INTERNAL_ERROR = -32099
