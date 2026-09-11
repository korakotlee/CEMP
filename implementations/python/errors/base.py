"""Base error payload models and root CEMP exception."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field

from errors.codes import CEMPErrorCode


class CEMPErrorPayload(BaseModel):
    """Structured error payload required for conforming CEMP error responses."""

    code: int
    name: str
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    recoverable: bool = True
    suggested_action: str = ""


class CEMPError(Exception):
    """Base class for all structured CEMP protocol exceptions."""

    def __init__(
        self,
        code: CEMPErrorCode | int,
        name: str,
        message: str,
        data: dict[str, Any] | None = None,
        recoverable: bool = True,
        suggested_action: str = "",
    ):
        super().__init__(message)
        self.code = int(code)
        self.name = name
        self.message = message
        self.data = data or {}
        self.recoverable = recoverable
        self.suggested_action = suggested_action

    def to_payload(self) -> CEMPErrorPayload:
        """Convert exception to Pydantic validation model."""
        return CEMPErrorPayload(
            code=self.code,
            name=self.name,
            message=self.message,
            data=self.data,
            recoverable=self.recoverable,
            suggested_action=self.suggested_action,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to standard dictionary payload."""
        return self.to_payload().model_dump()

    def to_call_tool_result(self) -> CallToolResult:
        """Format exception as an MCP CallToolResult with isError=True."""
        payload = self.to_dict()
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False))],
            structuredContent=payload,
        )


def format_cemp_error(exc: Exception) -> CallToolResult:
    """Format any exception into a standard CEMP CallToolResult."""
    if isinstance(exc, CEMPError):
        return exc.to_call_tool_result()
    # Unhandled unexpected exceptions wrapped safely
    from errors.system_errors import InternalServerError

    internal = InternalServerError(str(exc))
    return internal.to_call_tool_result()
