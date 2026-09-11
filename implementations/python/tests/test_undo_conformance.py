"""Conformance tests for undo_last tool and auto-rollback mechanics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.types import CallToolResult


@pytest.mark.asyncio
async def test_undo_last_conformance_schema(
    server_instance, schema_validator, temp_git_repo: Path, monkeypatch
):
    """Validate undo_last request and response against protocol/schemas/undo_last.json."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))

    # 1. Propose and apply an edit to README.md
    prop_res = await server_instance.call_tool(
        "propose_edit",
        {
            "path": "README.md",
            "old_str": "Test Repository",
            "new_str": "Workspace",
            "expected_occurrences": 1,
        },
    )
    patch_id = json.loads(prop_res.content[0].text)["patch_id"]
    await server_instance.call_tool("apply_patch", {"patch_id": patch_id})

    readme_content = (temp_git_repo / "README.md").read_text(encoding="utf-8")
    assert "Workspace" in readme_content

    # 2. Invoke undo_last
    undo_req = {"path": "README.md"}
    schema_validator("undo_last", undo_req, target="parameters")

    undo_res: CallToolResult = await server_instance.call_tool("undo_last", undo_req)
    assert undo_res.isError is False
    payload = json.loads(undo_res.content[0].text)
    schema_validator("undo_last", payload, target="response")

    assert payload["status"] == "reverted"
    assert payload["reverted_patch_id"] == patch_id
    assert "README.md" in payload["reverted_files"]

    # File on disk must be reverted back
    restored_content = (temp_git_repo / "README.md").read_text(encoding="utf-8")
    assert "Test Repository" in restored_content


@pytest.mark.asyncio
async def test_undo_last_empty_history(server_instance, temp_git_repo: Path, monkeypatch):
    """Validate undo_last returns -32060 (E_UNDO_UNAVAILABLE) when no patches are available."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))

    res: CallToolResult = await server_instance.call_tool("undo_last", {})
    assert res.isError is True
    error_payload = json.loads(res.content[0].text)
    assert error_payload["code"] == -32060
    assert error_payload["name"] == "E_UNDO_UNAVAILABLE"


@pytest.mark.asyncio
async def test_apply_patch_auto_rollback_conformance(
    server_instance, temp_git_repo: Path, monkeypatch
):
    """Validate apply_patch auto-rollback on syntax error via MCP tool call."""
    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(temp_git_repo))

    target = temp_git_repo / "code.py"
    target.write_text("x = 100\n", encoding="utf-8")

    prop_res = await server_instance.call_tool(
        "propose_edit",
        {
            "path": "code.py",
            "old_str": "x = 100",
            "new_str": "def invalid_syntax(\n",
            "expected_occurrences": 1,
        },
    )
    patch_id = json.loads(prop_res.content[0].text)["patch_id"]

    apply_res = await server_instance.call_tool(
        "apply_patch", {"patch_id": patch_id, "verify_syntax": True}
    )
    assert apply_res.isError is True
    error_payload = json.loads(apply_res.content[0].text)
    assert error_payload["code"] in (-32040, -32042)
    assert target.read_text(encoding="utf-8") == "x = 100\n"
