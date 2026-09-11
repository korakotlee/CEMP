"""CEMP FastMCP Server reference implementation over stdio transport."""

from __future__ import annotations

import functools
import inspect
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent

from core.engine import (
    apply_patch as core_apply_patch,
)
from core.engine import (
    get_file_hash as core_get_file_hash,
)
from core.engine import (
    propose_edit as core_propose_edit,
)
from core.engine import (
    propose_line_edit as core_propose_line_edit,
)
from core.engine import (
    read_file as core_read_file,
)
from core.engine import (
    search_code as core_search_code,
)
from errors import (
    OccurrenceMismatchError,
    format_cemp_error,
)

# Centralized stderr logging setup to prevent stdout protocol pollution
_logger = logging.getLogger("cemp")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)


def debug_log(msg: str, **context: Any) -> None:
    """Common timestamped debug log callable from anywhere in the codebase."""
    now = datetime.now(timezone.utc).isoformat()
    extra_str = f" | {context}" if context else ""
    _logger.debug(f"[{now}] {msg}{extra_str}")


# FastMCP Server Initialization
mcp_server = FastMCP(
    name="cemp",
    instructions="Code Editing MCP Protocol (CEMP) reference server v1.0.0-draft",
)
mcp_server.version = "1.0.0-draft"


def cemp_tool(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator registering an MCP tool with centralized CEMP error interception."""
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> CallToolResult:
            try:
                res = await func(*args, **kwargs)
                if isinstance(res, CallToolResult):
                    return res
                if isinstance(res, dict):
                    return CallToolResult(
                        content=[
                            TextContent(type="text", text=json.dumps(res, ensure_ascii=False))
                        ],
                        structuredContent=res,
                    )
                return CallToolResult(content=[TextContent(type="text", text=str(res))])
            except Exception as exc:
                debug_log("Exception intercepted in tool", tool=func.__name__, error=str(exc))
                return format_cemp_error(exc)

        async_wrapper.__annotations__["return"] = CallToolResult
        return mcp_server.tool()(async_wrapper)

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> CallToolResult:
        try:
            res = func(*args, **kwargs)
            if isinstance(res, CallToolResult):
                return res
            if isinstance(res, dict):
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(res, ensure_ascii=False))],
                    structuredContent=res,
                )
            return CallToolResult(content=[TextContent(type="text", text=str(res))])
        except Exception as exc:
            debug_log("Exception intercepted in tool", tool=func.__name__, error=str(exc))
            return format_cemp_error(exc)

    sync_wrapper.__annotations__["return"] = CallToolResult
    return mcp_server.tool()(sync_wrapper)


@cemp_tool
def ping_error() -> CallToolResult:
    """Conformance test tool verifying standardized CEMP error formatting."""
    raise OccurrenceMismatchError(
        message="Conformance ping error verification",
        data={"expected_occurrences": 1, "actual_occurrences": 2},
    )


@cemp_tool
def read_file(path: str, line_range: list[int] | None = None) -> dict[str, Any]:
    """Read file contents with 1-indexed line numbers and content SHA-256 hash for CAS operations.

    Args:
        path: Path to the target file, absolute or relative to workspace root.
        line_range: Optional [start_line, end_line] 1-indexed inclusive range.
    """
    debug_log("Invoking read_file", path=path, line_range=line_range)
    return core_read_file(path=path, line_range=line_range)


@cemp_tool
def get_file_hash(path: str) -> dict[str, Any]:
    """Retrieve optimistic SHA-256 CAS content hash for a file.

    Args:
        path: Path to the target file, absolute or relative to workspace root.
    """
    debug_log("Invoking get_file_hash", path=path)
    return core_get_file_hash(path=path)


@cemp_tool
def search_code(
    pattern: str,
    path_glob: str = "**/*",
    regex: bool = False,
    context_lines: int = 3,
) -> dict[str, Any]:
    """Search for literal text or regex patterns across workspace files.

    Args:
        pattern: Search string or regular expression pattern.
        path_glob: Glob pattern filtering target paths (e.g. 'src/**/*.py').
        regex: If true, pattern is parsed as a regular expression.
        context_lines: Number of lines of surrounding context to include before and after matches.
    """
    debug_log("Invoking search_code", pattern=pattern, path_glob=path_glob, regex=regex)
    return core_search_code(
        pattern=pattern,
        path_glob=path_glob,
        regex=regex,
        context_lines=context_lines,
    )


@cemp_tool
def propose_edit(
    path: str,
    old_str: str,
    new_str: str,
    expected_occurrences: int = 1,
) -> dict[str, Any]:
    """Propose an exact string replacement with strict occurrence checking and diff preview.

    Args:
        path: Path to target file within workspace.
        old_str: Exact text substring to be replaced.
        new_str: Replacement text content.
        expected_occurrences: Strict expected count of matches (default: 1).
    """
    debug_log(
        "Invoking propose_edit",
        path=path,
        expected_occurrences=expected_occurrences,
    )
    return core_propose_edit(
        path=path,
        old_str=old_str,
        new_str=new_str,
        expected_occurrences=expected_occurrences,
    )


@cemp_tool
def propose_line_edit(
    path: str,
    start_line: int,
    end_line: int,
    new_content: str,
    content_hash: str,
) -> dict[str, Any]:
    """Propose a line range edit protected by Compare-And-Swap (CAS) hash validation.

    Args:
        path: Path to target file within workspace.
        start_line: 1-indexed starting line number of the target block.
        end_line: 1-indexed inclusive ending line number of the target block.
        new_content: New replacement content for the specified line range.
        content_hash: SHA-256 hash of the target file content obtained from read_file.
    """
    debug_log(
        "Invoking propose_line_edit",
        path=path,
        start_line=start_line,
        end_line=end_line,
        content_hash=content_hash,
    )
    return core_propose_line_edit(
        path=path,
        start_line=start_line,
        end_line=end_line,
        new_content=new_content,
        content_hash=content_hash,
    )


@cemp_tool
def apply_patch(
    patch_id: str,
    tx_id: str | None = None,
    verify_syntax: bool = True,
) -> dict[str, Any]:
    """Apply a proposed patch to disk or stage it into an active transaction.

    Args:
        patch_id: Identifier of the staged patch from propose_edit or propose_line_edit.
        tx_id: Optional transaction ID.
        verify_syntax: Whether to run language syntax validation hooks post-write.
    """
    debug_log(
        "Invoking apply_patch",
        patch_id=patch_id,
        tx_id=tx_id,
        verify_syntax=verify_syntax,
    )
    return core_apply_patch(
        patch_id=patch_id,
        tx_id=tx_id,
        verify_syntax=verify_syntax,
    )


def main() -> None:
    """Run FastMCP CEMP server over stdio transport."""
    debug_log("Booting CEMP FastMCP server", version=mcp_server.version)
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
