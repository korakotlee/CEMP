# CEMP Python Reference Implementation

This directory contains the Python reference implementation of the **Code Editing MCP Protocol (CEMP)** built with FastMCP over stdio transport.

## Architecture

- **`server.py`**: FastMCP server instance (`cemp`, version `1.0.0-draft`), centralized stdio transport lifecycle, and diagnostic logging routed strictly to `sys.stderr`.
- **`errors/`**: Standardized CEMP error registry and typed exception hierarchy conforming to `protocol/error-codes.md`:
  - `codes.py`: Standard error codes (`-32000` to `-32099`).
  - `base.py`: `CEMPError` base exception and payload formatting (`format_cemp_error`).
  - `proposal_errors.py`: Proposal, match, and CAS exceptions (`NoMatchError`, `StaleHashError`, etc.).
  - `system_errors.py`: Filesystem, transaction, and syntax exceptions (`PathTraversalError`, `SyntaxErrorCEMP`, etc.).
- **`tests/`**:
  - `conftest.py`: Reusable test fixtures (`temp_git_repo`, `schema_validator`, `server_instance`).
  - `test_conformance.py`: Protocol conformance tests validating metadata, stdio cleanliness, and error serialization.

## Quickstart

### Prerequisites
- Python 3.11+
- `uv` package manager

### Sync Dependencies
```bash
uv sync
```

### Run Server Locally
```bash
uv run python -m server
```

### Run Tests & Verification
```bash
# Run test suite
uv run pytest

# Check code formatting & linting
uv run ruff check .
uv run ruff format --check .
```
