# CEMP Python Reference Implementation

This directory contains the Python reference implementation of the **Code Editing MCP Protocol (CEMP)** built with FastMCP over stdio transport.

## Architecture

- **`server.py`**: FastMCP server instance (`cemp`, version `1.0.0-draft`), centralized stdio transport lifecycle, diagnostic logging routed strictly to `sys.stderr`, and registered CEMP tools (`read_file`, `get_file_hash`, `search_code`, `ping_error`).
- **`core/`**: Deterministic inspection engine and workspace protection:
  - `hasher.py`: Line ending normalization (`\r\n` to `\n`) and SHA-256 CAS digest computation.
  - `workspace.py`: Workspace boundary confinement, path resolution, and sensitive file protection (`.git/`, `.env`).
  - `engine.py`: Inspection primitives (`read_file`, `get_file_hash`, `search_code`) conforming to protocol schemas.
- **`errors/`**: Standardized CEMP error registry and typed exception hierarchy conforming to `protocol/error-codes.md`:
  - `codes.py`: Standard error codes (`-32000` to `-32099`).
  - `base.py`: `CEMPError` base exception and payload formatting (`format_cemp_error`).
  - `proposal_errors.py`: Proposal, match, and CAS exceptions (`NoMatchError`, `InvalidRangeError`, `StaleHashError`, etc.).
  - `system_errors.py`: Filesystem, transaction, and syntax exceptions (`PathTraversalError`, `FileNotFoundCEMPError`, etc.).
- **`tests/`**:
  - `conftest.py`: Reusable test fixtures (`temp_git_repo`, `schema_validator`, `server_instance`).
  - `test_conformance.py`: Protocol conformance tests validating metadata, schemas, stdio cleanliness, and error serialization.
  - `test_hasher.py`: Unit tests for line normalization and SHA-256 CAS computation.
  - `test_workspace.py`: Unit tests for directory traversal prevention and sensitive path security.
  - `test_inspection.py`: Unit tests for `read_file`, `get_file_hash`, and `search_code`.

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
