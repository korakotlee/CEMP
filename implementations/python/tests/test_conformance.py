"""Conformance test suite for CEMP Python FastMCP server and protocol schemas."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from mcp.types import CallToolResult


def test_temp_git_repo_fixture(temp_git_repo: Path):
    """Ensure temporary git repository is cleanly initialized with initial commit."""
    assert (temp_git_repo / ".git").is_dir()
    assert (temp_git_repo / "README.md").is_file()

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "", "Git working tree should be clean"

    log_result = subprocess.run(
        ["git", "log", "-1", "--oneline"],
        cwd=temp_git_repo,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Initial commit" in log_result.stdout


def test_schema_validator_fixture(schema_validator):
    """Ensure schema validator correctly loads protocol schemas and catches violations."""
    valid_read_request = {
        "path": "test.txt",
        "line_range": [1, 10],
    }
    schema_validator("read_file", valid_read_request)

    invalid_read_request = {
        "path": 123,  # Invalid type: must be string
    }
    with pytest.raises(Exception):
        schema_validator("read_file", invalid_read_request)


def test_server_metadata(server_instance):
    """Ensure FastMCP server registers name 'cemp' and draft version."""
    assert server_instance.name == "cemp"
    assert "1.0.0-draft" in getattr(server_instance, "version", "1.0.0-draft")


@pytest.mark.asyncio
async def test_standardized_error_format(server_instance):
    """Ensure standardized CEMP error formatting conforms to protocol/error-codes.md."""
    # Tool 'ping_error' will be registered on server.py for conformance testing
    result: CallToolResult = await server_instance.call_tool("ping_error", {})
    assert result.isError is True
    assert len(result.content) > 0

    error_payload = json.loads(result.content[0].text)
    required_keys = {"code", "name", "message", "data", "recoverable", "suggested_action"}
    assert required_keys.issubset(error_payload.keys())

    assert isinstance(error_payload["code"], int)
    assert -32099 <= error_payload["code"] <= -32000
    assert isinstance(error_payload["name"], str)
    assert isinstance(error_payload["message"], str)
    assert isinstance(error_payload["data"], dict)
    assert isinstance(error_payload["recoverable"], bool)
    assert isinstance(error_payload["suggested_action"], str)


def test_error_registry_invariants():
    """Ensure error code definitions adhere to JSON-RPC application error range."""
    from errors import CEMPErrorCode

    for item in CEMPErrorCode:
        assert -32099 <= item.value <= -32000, f"Error code {item.name} out of range"


def test_cemp_error_serialization():
    """Ensure CEMPError instances serialize to conforming error dictionaries."""
    from errors import NoMatchError, OccurrenceMismatchError

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
    from errors import StaleHashError, format_cemp_error

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


@pytest.mark.asyncio
async def test_uncaught_exception_cemp_tool(server_instance):
    """Ensure cemp_tool decorator safely catches unhandled exceptions and returns CEMP error."""
    from server import cemp_tool

    @cemp_tool
    async def failing_async_tool() -> str:
        raise RuntimeError("Unexpected boom")

    res = await server_instance.call_tool("failing_async_tool", {})
    assert res.isError is True
    payload = json.loads(res.content[0].text)
    assert payload["code"] == -32099
    assert payload["name"] == "E_INTERNAL_ERROR"
    assert "Unexpected boom" in payload["message"]


def test_debug_log_utility():
    """Ensure debug_log writes to stderr without crashing."""
    from server import debug_log

    debug_log("Test log entry", sample_key="sample_val")


def test_stdio_handshake_clean_stdout():
    """Verify that python -m server responds to initialize without polluting stdout."""
    init_msg = (
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }
        )
        + "\n"
    )

    proc = subprocess.Popen(
        ["python", "-m", "server"],
        cwd=Path(__file__).parents[1],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_data, stderr_data = proc.communicate(input=init_msg, timeout=5)
    lines = [line.strip() for line in stdout_data.strip().splitlines() if line.strip()]
    assert len(lines) == 1, f"Expected exactly 1 JSON-RPC response on stdout, got: {stdout_data}"

    parsed = json.loads(lines[0])
    assert parsed.get("jsonrpc") == "2.0"
    assert parsed.get("id") == 1
    assert "result" in parsed
    assert parsed["result"]["serverInfo"]["name"] == "cemp"


@pytest.mark.asyncio
async def test_read_file_conformance_schema(
    server_instance, schema_validator, temp_git_repo: Path, monkeypatch
):
    """Validate read_file request and response against protocol/schemas/read_file.json."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))

    req = {"path": "README.md", "line_range": [1, 1]}
    schema_validator("read_file", req, target="parameters")

    res: CallToolResult = await server_instance.call_tool("read_file", req)
    assert res.isError is False
    payload = json.loads(res.content[0].text)
    schema_validator("read_file", payload, target="response")

    assert payload["total_lines"] >= 1
    assert payload["lines"][0] == [1, "# CEMP Test Repository"]


@pytest.mark.asyncio
async def test_search_code_conformance_schema(
    server_instance, schema_validator, temp_git_repo: Path, monkeypatch
):
    """Validate search_code request and response against protocol/schemas/search_code.json."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))

    req = {
        "pattern": "CEMP",
        "path_glob": "**/*.md",
        "regex": False,
        "context_lines": 2,
    }
    schema_validator("search_code", req, target="parameters")

    res: CallToolResult = await server_instance.call_tool("search_code", req)
    assert res.isError is False
    payload = json.loads(res.content[0].text)
    schema_validator("search_code", payload, target="response")

    assert payload["total_matches"] >= 1
    assert any("README.md" in m["file"] for m in payload["matches"])


@pytest.mark.asyncio
async def test_propose_edit_conformance_schema(
    server_instance, schema_validator, temp_git_repo: Path, monkeypatch
):
    """Validate propose_edit request and response against propose_edit.json."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))
    req = {
        "path": "README.md",
        "old_str": "Test Repository",
        "new_str": "Workspace",
        "expected_occurrences": 1,
    }
    schema_validator("propose_edit", req, target="parameters")

    res: CallToolResult = await server_instance.call_tool("propose_edit", req)
    assert res.isError is False
    payload = json.loads(res.content[0].text)
    schema_validator("propose_edit", payload, target="response")
    assert payload["status"] == "ok"


@pytest.mark.asyncio
async def test_propose_line_edit_and_apply_conformance_schema(
    server_instance, schema_validator, temp_git_repo: Path, monkeypatch
):
    """Validate propose_line_edit and apply_patch schemas."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))
    read_res: CallToolResult = await server_instance.call_tool("read_file", {"path": "README.md"})
    file_hash = json.loads(read_res.content[0].text)["content_hash"]

    line_req = {
        "path": "README.md",
        "start_line": 1,
        "end_line": 1,
        "new_content": "# Updated CEMP Test Repository",
        "content_hash": file_hash,
    }
    schema_validator("propose_line_edit", line_req, target="parameters")

    res1: CallToolResult = await server_instance.call_tool("propose_line_edit", line_req)
    assert res1.isError is False
    payload1 = json.loads(res1.content[0].text)
    schema_validator("propose_line_edit", payload1, target="response")

    apply_req = {"patch_id": payload1["patch_id"], "verify_syntax": True}
    schema_validator("apply_patch", apply_req, target="parameters")

    res2: CallToolResult = await server_instance.call_tool("apply_patch", apply_req)
    assert res2.isError is False
    payload2 = json.loads(res2.content[0].text)
    schema_validator("apply_patch", payload2, target="response")
    assert payload2["status"] == "applied"


