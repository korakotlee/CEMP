"""Helper utilities and logging for CEMP FastMCP server."""

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

from errors import format_cemp_error

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


def make_cemp_tool(mcp_server: FastMCP) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a tool registration decorator with standardized CEMP error interception."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
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
                        content=[
                            TextContent(type="text", text=json.dumps(res, ensure_ascii=False))
                        ],
                        structuredContent=res,
                    )
                return CallToolResult(content=[TextContent(type="text", text=str(res))])
            except Exception as exc:
                debug_log("Exception intercepted in tool", tool=func.__name__, error=str(exc))
                return format_cemp_error(exc)

        sync_wrapper.__annotations__["return"] = CallToolResult
        return mcp_server.tool()(sync_wrapper)

    return decorator
