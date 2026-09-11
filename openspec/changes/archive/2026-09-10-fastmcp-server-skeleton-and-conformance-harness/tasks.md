## 1. Environment Setup & Test Harness (TDD Setup)

- [x] 1.1 Scaffold `implementations/python/pyproject.toml` with `mcp[cli]>=1.2.0`, `pydantic>=2.0`, `jsonschema>=4.20`, `ruff`, and `pytest`, and verify dependency resolution succeeds via `uv sync` or `uv lock`.
- [x] 1.2 Implement test fixtures in `implementations/python/tests/conftest.py` for temporary git repositories, in-memory FastMCP client sessions, and JSON schema loading from `protocol/schemas/`, verifying test fixtures initialize cleanly.
- [x] 1.3 Create failing conformance test cases in `implementations/python/tests/test_conformance.py` covering server metadata, clean boot, schema validation, and standardized error response formatting, verifying that the tests fail against an unconfigured server.

## 2. Server Implementation & Error Handling (Feature Implementation)

- [x] 2.1 Implement `implementations/python/errors.py` with the CEMP exception hierarchy and standardized JSON-RPC error payload formatting matching `protocol/error-codes.md`, and verify error mapping tests pass.
- [x] 2.2 Implement the FastMCP server skeleton in `implementations/python/server.py` with server instance metadata ("cemp", "1.0.0-draft"), stderr logging routing, and error interceptors, verifying that `tests/test_conformance.py` passes completely.
- [x] 2.3 Verify stdio execution entrypoint (`uv run python -m server`) handles MCP initialization handshakes without polluting stdout streams.

## 3. Refactoring, Linting & Documentation

- [x] 3.1 Verify file line lengths remain strictly under 300 lines and ensure all lint and formatting checks pass with `ruff check` and `ruff format --check`.
- [x] 3.2 Update `README.md` and repository documentation reflecting the Python implementation skeleton, test commands, and architectural layout.
- [x] 3.3 Update `docs/user-guide.md` how to add CEMP MCP server to work with the coding agent.
