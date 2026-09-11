## Why

Without an early server skeleton and test harness, domain modules (hasher, engine, storage) risk being developed in isolation with mocked unit tests, deferring MCP transport integration and schema validation until the end of the project. Establishing a running FastMCP server skeleton with stdio transport and a schema-driven test harness enables continuous verification of tools and error formats from Day 1.

## What Changes

- Scaffold `implementations/python/pyproject.toml` managing dependencies (`mcp[cli]`, `pydantic`, `jsonschema`, `ruff`, `pytest`).
- Implement `implementations/python/server.py` establishing the FastMCP server instance (`cemp`, version `1.0.0-draft`) over stdio transport.
- Implement standardized CEMP exception hierarchy and error handling to serialize errors according to `protocol/error-codes.md`.
- Implement `implementations/python/tests/conftest.py` with fixtures for in-memory FastMCP client testing, dynamic JSON schema validation from `protocol/schemas/`, and isolated temporary git repositories.
- Implement `implementations/python/tests/test_conformance.py` validating server startup, protocol schema conformance, and standardized error response formatting.

## Capabilities

### New Capabilities
- `server-runtime`: FastMCP server initialization, stdio transport lifecycle, standardized CEMP error response formatting, and schema validation test harness.

### Modified Capabilities

## Impact

- **New files**:
  - `implementations/python/pyproject.toml`
  - `implementations/python/server.py`
  - `implementations/python/tests/conftest.py`
  - `implementations/python/tests/test_conformance.py`
- **Dependencies**: Python 3.11+, `mcp[cli]>=1.2.0`, `pydantic>=2.0`, `jsonschema>=4.20`, `ruff`, `pytest`.
- **System**: Establishes the core runner entrypoint (`uv run python -m server`) for all upcoming CEMP MCP tool integrations.
