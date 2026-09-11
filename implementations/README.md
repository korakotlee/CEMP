# CEMP Python Reference Implementation

A high-integrity, provider-agnostic macOS Model Context Protocol (MCP) server implementing the **Code Editing MCP Protocol (CEMP)**.

---

## 1. Executive Summary & Objectives

The Python reference implementation provides a concrete, production-grade realization of the CEMP specification (`protocol/SPECIFICATION.md`). It transforms AI code editing from dangerous raw stream editing (`sed`, `awk`) into a deterministic, two-phase committed operation with:

1. **Two-Phase Commit (2PC):** Proposal of diffs in memory without premature disk writes.
2. **Deterministic Grounding:** Strict literal occurrence counts and SHA-256 Compare-And-Swap (CAS) guards.
3. **Atomic Filesystem Safety:** APFS-safe atomic temporary file replacement (`flush`, `fsync`, `os.replace`).
4. **Zero-Pollution Rollback:** Git plumbing integration (`git hash-object`, `git cat-file`) without dummy commits or log pollution.
5. **Post-Write Syntax Verification:** Automated compiler checks (`py_compile`, `node --check`) with instant reversion upon error.

---

## 2. Recommended Tech Stack & Architecture

### Core Stack Decisions

| Component | Choice | Rationale & Trade-offs |
|---|---|---|
| **Runtime** | Python 3.11+ | Modern typing (`typing.Self`, union types), fast startup, macOS native availability. |
| **Package Manager** | `uv` | Instant dependency resolution, zero-friction virtualenv management, native script runner. |
| **MCP Server Framework** | `FastMCP` (`mcp[cli]`) | Official standard, declarative `@mcp.tool()` decorators, automatic schema generation, stdio and SSE transport support. |
| **Data Validation** | `pydantic` v2 | Schema validation aligning with `protocol/schemas/*.json`, strict type casting, JSON Schema export. |
| **Diffing Engine** | `difflib` (Standard Library) | Zero external dependency, standard unified diff formatting, deterministic line computation. |
| **Filesystem Safety** | `pathlib` + `os` (`os.replace`, `os.fsync`) | POSIX/APFS atomic swap guarantee; prevents corrupted or partial file states. |
| **VCS / Rollback** | Native `git` CLI via `subprocess` | Direct Git plumbing (`git hash-object`, `git cat-file`) without the bloat and security pitfalls of `GitPython`. |
| **Verification Hooks** | Extensible Hook Registry | Native `py_compile` for Python, subprocess execution for `node --check` and `tsc --noEmit`. |
| **Testing & Quality** | `pytest`, `pytest-asyncio`, `ruff` | Fast, comprehensive unit testing and strict PEP 8 formatting/linting. |

---

## 3. Package Structure

```text
implementations/python/
├── pyproject.toml              # uv project configuration, dependencies, and entrypoints
├── server.py                   # FastMCP server registration and stdio entrypoint
├── core/
│   ├── __init__.py
│   ├── engine.py               # Read, proposal generation, and diff building
│   ├── hasher.py               # SHA-256 computation and CAS validators
│   ├── storage.py              # Atomic disk writes (temp file + fsync + os.replace)
│   ├── transactions.py         # Multi-file transaction staging and atomic commit
│   └── git_undo.py             # Zero-pollution Git object store backup and restoration
├── verification/
│   ├── __init__.py
│   ├── registry.py             # Verification hook orchestrator
│   ├── python_checker.py       # py_compile / ast syntax verification
│   └── node_checker.py         # node --check syntax verification
└── tests/
    ├── conftest.py             # Temporary repos and fixtures
    ├── test_inspection.py      # read_file, search_code, get_file_hash
    ├── test_propose_edit.py    # Occurrence enforcement and diff previews
    ├── test_cas_line_edit.py   # Stale hash rejection and line replacement
    ├── test_atomic_replace.py  # Filesystem swap and crash resilience
    ├── test_verification.py    # Auto-rollback on syntax failure
    ├── test_transactions.py    # Multi-file atomic batch commits
    └── test_git_undo.py        # Zero-pollution undo mechanics
```

---

## 4. Phased Implementation Roadmap (Walking Skeleton Approach)

### Phase 1: FastMCP Server Skeleton & Conformance Harness (Ticket 001)
- Scaffold `pyproject.toml` with `mcp[cli]`, `pydantic`, `jsonschema`, `ruff`, and `pytest`.
- Create `server.py` with FastMCP stdio transport and centralized JSON-RPC error mapping.
- Set up `tests/conftest.py` and `tests/test_conformance.py` schema validator fixture to enable live testing of every tool during development.

### Phase 2: Core Foundation & Inspection Tools (Ticket 002)
- Implement `core/hasher.py`: SHA-256 calculation and line normalization.
- Implement and mount inspection tools on `server.py`:
  - `read_file`: Line-numbered output, boundary slicing, and file content hash.
  - `get_file_hash`: Optimistic CAS baseline digest.
  - `search_code`: Contextual search with regex and literal modes.
- Validate live via `pytest tests/test_conformance.py`.

### Phase 3: Proposal Engine & Two-Phase Commit (Ticket 003)
- Implement patch cache manager with 15-minute TTL.
- Implement and mount `propose_edit` (strict occurrence check, unified diffs via `difflib`).
- Implement and mount `propose_line_edit` (1-indexed CAS pre-condition validation).
- Implement and mount `apply_patch` (atomic sibling file creation, `fsync`, and `os.replace`).
- Validate live via `pytest tests/test_conformance.py`.

### Phase 4: Zero-Pollution Undo & Verification Hooks (Ticket 004)
- Implement `core/git_undo.py` leveraging Git plumbing (`git hash-object -w`, `git cat-file -p`).
- Implement `verification/` hook registry (`py_compile`, `node --check`).
- Integrate auto-rollback on syntax failure inside `apply_patch`.
- Implement and mount `undo_last` tool on `server.py`.
- Validate live via `pytest tests/test_conformance.py`.

### Phase 5: Multi-File Transactions & Full Conformance (Ticket 005)
- Implement `core/transactions.py`:
  - `begin_transaction`, isolated staging workspace.
  - `commit_transaction` with all-or-nothing multi-file atomic swap.
  - `rollback_transaction` for safe discarding of staged edits.
- Mount transaction tools on `server.py`.
- Run complete end-to-end test suite confirming 100% protocol conformance across all schemas.

---

## 5. Local Setup & Execution

```bash
# Navigate to Python implementation directory
cd implementations/python

# Install dependencies and sync virtualenv
uv sync

# Run the CEMP FastMCP server
uv run python -m server

# Run tests
uv run pytest
```

