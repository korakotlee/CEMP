# CEMP Python Reference Implementation

This directory contains the Python reference implementation of the **Code Editing MCP Protocol (CEMP)** built with FastMCP over stdio transport.

## Architecture

- **`server.py`**: FastMCP server instance (`cemp`, version `1.0.0-draft`), centralized stdio transport lifecycle, diagnostic logging routed strictly to `sys.stderr`, and registered CEMP tools (`read_file`, `get_file_hash`, `search_code`, `propose_edit`, `propose_line_edit`, `apply_patch`, `undo_last`, `begin_transaction`, `commit_transaction`, `rollback_transaction`, `ping_error`).
- **`server_helpers.py`**: Logging configuration, timestamped debug log callable, and MCP tool exception formatting wrapper.
- **`core/`**: Deterministic inspection engine, two-phase commit, multi-file transaction coordinator, and Git-backed undo:
  - `hasher.py`: Line ending normalization (`\r\n` to `\n`) and SHA-256 CAS digest computation.
  - `workspace.py`: Workspace boundary confinement, path resolution, and sensitive file protection (`.git/`, `.env`).
  - `inspection.py`: Inspection primitives (`read_file`, `get_file_hash`, `search_code`) conforming to protocol schemas.
  - `patch_cache.py`: Ephemeral in-memory staging cache for proposal lifecycle and TTL management.
  - `storage.py`: Atomic file writes using sibling temporary files and `os.replace`.
  - `proposals.py`: Proposal generation and diff preview for exact-match and line-range edits.
  - `transactions.py`: Multi-file transaction management, isolated directory staging (`cemp_tx_<tx_id>`), CAS verification across all staged targets, batch atomic commit, and rollback coordination.
  - `git_undo.py`: Zero-pollution Git-backed snapshots (`git hash-object -w`), atomic rollbacks, and LIFO undo history.
  - `engine.py`: Central engine coordinating proposals, patch commit, multi-file transactions, and undo operations.
- **`verification/`**: Language-specific syntax checking hooks and registry:
  - `registry.py`: Extensible registry routing files to syntax checkers.
  - `python_checker.py`: Fast Python AST validation via standard library `py_compile`.
  - `node_checker.py`: JavaScript syntax validation via `node --check`.
- **`errors/`**: Standardized CEMP error registry and typed exception hierarchy conforming to `protocol/error-codes.md`:
  - `codes.py`: Standard error codes (`-32000` to `-32099`).
  - `base.py`: `CEMPError` base exception and payload formatting (`format_cemp_error`).
  - `proposal_errors.py`: Proposal, match, and CAS exceptions (`NoMatchError`, `InvalidRangeError`, `StaleHashError`, etc.).
  - `system_errors.py`: Filesystem, transaction, syntax, and undo exceptions (`TransactionActiveError`, `TransactionNotFoundError`, `RollbackTriggeredError`, `PathTraversalError`, `SyntaxErrorCEMP`, `UndoUnavailableError`, etc.).
- **`tests/`**:
  - `conftest.py`: Reusable test fixtures (`temp_git_repo`, `schema_validator`, `server_instance`, `clean_global_tx_state`).
  - `test_conformance.py`: Protocol conformance tests validating metadata, schemas, stdio cleanliness, and transaction schemas.
  - `test_errors.py`: Unit tests for standardized error serialization and exception formatting.
  - `test_hasher.py`: Unit tests for line normalization and SHA-256 CAS computation.
  - `test_workspace.py`: Unit tests for directory traversal prevention and sensitive path security.
  - `test_inspection.py`: Unit tests for `read_file`, `get_file_hash`, and `search_code`.
  - `test_patch_cache.py`: Unit tests for proposal cache storage and expiration.
  - `test_storage.py`: Unit tests for atomic file writes and crash safety.
  - `test_two_phase_commit.py`: Unit tests for two-phase commit, CAS protection, and post-write syntax verification.
  - `test_transactions.py`: Unit tests for multi-file transaction lifecycle, transactional staging, CAS drift detection, batch atomic commit, and auto-rollback.
  - `test_git_undo.py`: Unit tests for Git plumbing snapshots and zero commit/reflog pollution.
  - `test_verification.py`: Unit tests for Python and Node syntax checkers.
  - `test_undo_conformance.py`: Conformance tests for `undo_last` and automatic syntax rollback.


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
