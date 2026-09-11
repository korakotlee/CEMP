"""Unit tests for inspection engine: read_file, get_file_hash, and search_code."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.engine import get_file_hash, read_file, search_code
from errors import InvalidRangeError


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    """Create sample files in temporary workspace for inspection testing."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    calc_file = src_dir / "calc.py"
    calc_file.write_text(
        "def add(a, b):\n"
        "    return a + b\n"
        "\n"
        "def sub(a, b):\n"
        "    return a - b\n",
        encoding="utf-8",
    )

    docs_file = tmp_path / "README.md"
    docs_file.write_text("# Math Lib\n\nContains add and sub functions.\n", encoding="utf-8")

    return tmp_path


def test_read_file_full(sample_workspace: Path):
    """Verify read_file returns 1-indexed lines, content_hash, and total_lines."""
    res = read_file("src/calc.py", workspace_root=sample_workspace)
    assert res["path"] == "src/calc.py"
    assert res["total_lines"] == 5
    assert len(res["lines"]) == 5
    assert res["lines"][0] == [1, "def add(a, b):"]
    assert res["lines"][1] == [2, "    return a + b"]
    assert res["lines"][4] == [5, "    return a - b"]
    assert len(res["content_hash"]) == 64


def test_read_file_line_range(sample_workspace: Path):
    """Verify read_file with inclusive [start_line, end_line] 1-indexed range."""
    res = read_file("src/calc.py", line_range=[2, 4], workspace_root=sample_workspace)
    assert res["path"] == "src/calc.py"
    assert res["total_lines"] == 5
    assert len(res["lines"]) == 3
    assert res["lines"][0] == [2, "    return a + b"]
    assert res["lines"][1] == [3, ""]
    assert res["lines"][2] == [4, "def sub(a, b):"]


def test_read_file_invalid_ranges(sample_workspace: Path):
    """Verify read_file raises InvalidRangeError for out-of-bounds ranges."""
    # Zero or negative start line
    with pytest.raises(InvalidRangeError) as exc_0:
        read_file("src/calc.py", line_range=[0, 3], workspace_root=sample_workspace)
    assert exc_0.value.code == -32003

    # Inverted range
    with pytest.raises(InvalidRangeError) as exc_inv:
        read_file("src/calc.py", line_range=[4, 2], workspace_root=sample_workspace)
    assert exc_inv.value.code == -32003

    # End line exceeds total lines
    with pytest.raises(InvalidRangeError) as exc_oob:
        read_file("src/calc.py", line_range=[1, 10], workspace_root=sample_workspace)
    assert exc_oob.value.code == -32003


def test_read_file_empty_file(sample_workspace: Path):
    """Verify read_file on empty file returns 0 total lines and empty line array."""
    empty_file = sample_workspace / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    res = read_file("empty.txt", workspace_root=sample_workspace)
    assert res["total_lines"] == 0
    assert res["lines"] == []
    assert res["content_hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_get_file_hash(sample_workspace: Path):
    """Verify get_file_hash returns identical hash as read_file without lines."""
    read_res = read_file("src/calc.py", workspace_root=sample_workspace)
    hash_res = get_file_hash("src/calc.py", workspace_root=sample_workspace)

    assert hash_res["path"] == "src/calc.py"
    assert hash_res["content_hash"] == read_res["content_hash"]


def test_search_code_literal(sample_workspace: Path):
    """Verify literal search_code with context lines and glob filtering."""
    res = search_code(
        pattern="return a + b",
        path_glob="**/*.py",
        regex=False,
        context_lines=1,
        workspace_root=sample_workspace,
    )
    assert res["total_matches"] == 1
    match = res["matches"][0]
    assert match["file"] == "src/calc.py"
    assert match["line"] == 2
    assert match["match_content"] == "    return a + b"
    assert match["context_before"] == ["def add(a, b):"]
    assert match["context_after"] == [""]


def test_search_code_regex(sample_workspace: Path):
    """Verify regular expression search_code matching multiple definitions."""
    res = search_code(
        pattern=r"def \w+\(a, b\):",
        path_glob="**/*.py",
        regex=True,
        context_lines=0,
        workspace_root=sample_workspace,
    )
    assert res["total_matches"] == 2
    lines = [m["line"] for m in res["matches"]]
    assert lines == [1, 4]
    assert res["matches"][0]["context_before"] == []
    assert res["matches"][0]["context_after"] == []


def test_search_code_no_match(sample_workspace: Path):
    """Verify search_code with non-matching pattern returns empty match list."""
    res = search_code(pattern="non_existent_symbol", workspace_root=sample_workspace)
    assert res["total_matches"] == 0
    assert res["matches"] == []


@pytest.mark.asyncio
async def test_server_tool_invocation_and_error_handling(
    server_instance, monkeypatch, sample_workspace: Path
):
    """Verify server.py tool wrappers and error formatting on live server instance."""
    import json

    monkeypatch.setenv("CEMP_WORKSPACE_ROOT", str(sample_workspace))

    # Test read_file via FastMCP server
    read_res = await server_instance.call_tool("read_file", {"path": "src/calc.py"})
    assert read_res.isError is False
    payload = json.loads(read_res.content[0].text)
    assert payload["total_lines"] == 5
    assert len(payload["lines"]) == 5

    # Test get_file_hash via FastMCP server
    hash_res = await server_instance.call_tool("get_file_hash", {"path": "src/calc.py"})
    assert hash_res.isError is False
    hash_payload = json.loads(hash_res.content[0].text)
    assert hash_payload["content_hash"] == payload["content_hash"]

    # Test error interception via FastMCP server (file not found)
    err_res = await server_instance.call_tool("read_file", {"path": "missing.py"})
    assert err_res.isError is True
    err_payload = json.loads(err_res.content[0].text)
    assert err_payload["code"] == -32051
    assert err_payload["name"] == "E_FILE_NOT_FOUND"

