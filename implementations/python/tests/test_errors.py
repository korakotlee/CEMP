"""Unit tests for CEMP error classes, serialization, and formatting utilities."""

from __future__ import annotations

import json

from errors import (
    CEMPErrorCode,
    NoMatchError,
    OccurrenceMismatchError,
    StaleHashError,
    format_cemp_error,
)


def test_error_registry_invariants():
    """Ensure error code definitions adhere to JSON-RPC application error range."""
    for item in CEMPErrorCode:
        assert -32099 <= item.value <= -32000, f"Error code {item.name} out of range"


def test_cemp_error_serialization():
    """Ensure CEMPError instances serialize to conforming error dictionaries."""
    err = NoMatchError()
    payload = err.to_dict()
    assert payload["code"] == -32000
    assert payload["name"] == "E_NO_MATCH"
    assert payload["recoverable"] is True
    assert payload["suggested_action"] == "RE_INSPECT"

    mismatch = OccurrenceMismatchError(
        "Expected 1 match, found 3",
        data={"expected": 1, "actual": 3, "matches": [14, 42, 89]},
    )
    m_payload = mismatch.to_dict()
    assert m_payload["code"] == -32001
    assert m_payload["data"]["actual"] == 3
    assert m_payload["suggested_action"] == "EXPAND_CONTEXT"


def test_format_cemp_error_utility():
    """Ensure format_cemp_error converts both CEMPError and generic exceptions."""
    stale = StaleHashError("Hash mismatch", data={"current_hash": "abcdef"})
    res1 = format_cemp_error(stale)
    assert res1.isError is True
    data1 = json.loads(res1.content[0].text)
    assert data1["code"] == -32010
    assert data1["name"] == "E_STALE_HASH"

    generic = ValueError("Invalid operation")
    res2 = format_cemp_error(generic)
    assert res2.isError is True
    data2 = json.loads(res2.content[0].text)
    assert data2["code"] == -32099
    assert data2["name"] == "E_INTERNAL_ERROR"
    assert "Invalid operation" in data2["message"]
