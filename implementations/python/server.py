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
    get_file_hash as core_get_file_hash,
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


def main() -> None:
    """Run FastMCP CEMP server over stdio transport."""
    debug_log("Booting CEMP FastMCP server", version=mcp_server.version)
    mcp_server.run(transport="stdio")


if __name__ == "__main__":
    main()
