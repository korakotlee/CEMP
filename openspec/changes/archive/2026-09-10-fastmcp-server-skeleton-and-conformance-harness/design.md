## Context

See `proposal.md` for motivation. This design establishes the walking skeleton of the CEMP Python implementation under `implementations/python/`. The architecture separates the MCP protocol facade (`server.py`) from upcoming domain modules (`core/`) and provides a test harness that loads the protocol schemas directly from `protocol/schemas/`.

## Goals / Non-Goals

**Goals:**
- Provide a runnable FastMCP server entrypoint via `uv run python -m server`.
- Implement a CEMP exception hierarchy and error mapper adhering to `protocol/error-codes.md`.
- Establish in-memory FastMCP test fixtures and a temporary Git repository fixture in `tests/conftest.py`.
- Implement `tests/test_conformance.py` validating server initialization, schema loading, and error serialization.
- Enforce strict file size limits (< 300 lines/file) and standard code styling via `ruff`.

**Non-Goals:**
- Implementing actual editing tools (`propose_edit`, `apply_patch`, `read_file`) - these will be mounted in tickets 002 through 006.
- Supporting daemonized network transports (SSE, Unix domain sockets) in this initial slice.
- Managing multi-user workspaces or distributed file locks.

## Decisions

### 1. FastMCP Framework Integration
- **Choice:** Use `FastMCP` from the official `mcp[cli]>=1.2.0` Python SDK.
- **Rationale:** FastMCP provides native Pydantic v2 argument validation, async tool dispatch, and standard stdio communication.
- **Alternatives Considered:** Raw `mcp.server.lowlevel` Server - rejected because it requires excessive boilerplate for JSON-RPC dispatch, schema generation, and routing.

### 2. Error Representation and Serialization
- **Choice:** Define a structured `CEMPError` base exception class and typed subclasses (`NoMatchError`, `OccurrenceMismatchError`, `StaleHashError`, etc.) that carry `code`, `name`, `data`, `recoverable`, and `suggested_action`.
- **Rationale:** Maps 1:1 with `protocol/error-codes.md`. FastMCP exception handlers serialize these fields into the tool error response payload.
- **Alternatives Considered:** Free-form string errors - rejected because automated agents require structured error codes and suggested actions for recovery loops.

### 3. Test Fixtures and In-Memory Execution
- **Choice:** FastMCP client session fixture that connects in-memory via memory transport or async pipe, paired with `jsonschema.Draft202012Validator`.
- **Rationale:** Allows sub-millisecond test iterations without spawning sub-processes. Loads real schemas from `protocol/schemas/` to ensure drift between spec and code is caught immediately.
- **Alternatives Considered:** Spawning external `python -m server` processes in tests - rejected due to subprocess startup latency and cross-platform timing flakiness.

### 4. Logging and Diagnostic Output
- **Choice:** Configure root and application logging handlers exclusively to `sys.stderr` with ISO-8601 timestamps.
- **Rationale:** MCP stdio transport requires `stdout` to be strictly clean JSON-RPC protocol frames. Any write to `stdout` breaks host parsing.

## Risks / Trade-offs

- **[Risk] Stdout Pollution:** Third-party libraries or stray `print()` calls write to `stdout`, corrupting the MCP JSON-RPC protocol framing.
  - **Mitigation:** Route all application logging strictly to `sys.stderr` in `server.py` logging initialization.
- **[Risk] Schema Path Resolution:** Test harness fails to locate `protocol/schemas/` when run from different working directories.
  - **Mitigation:** Resolve schema directory relative to repository root (`Path(__file__).parents[3] / "protocol" / "schemas"`).
- **[Risk] FastMCP Version Drift:** Changes in FastMCP client testing APIs across releases.
  - **Mitigation:** Pin `mcp>=1.2.0,<2.0.0` in `pyproject.toml` and test client integration during conformance test run.
