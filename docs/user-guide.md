# User Guide: Setting Up and Integrating CEMP MCP Server

This guide explains how to configure and run the CEMP Model Context Protocol (MCP) server to integrate safe, state-verified code editing capabilities into your AI coding agents.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)
2. [Quick Start & Local Execution](#2-quick-start--local-execution)
3. [Connecting CEMP to AI Coding Agents](#3-connecting-cemp-to-ai-coding-agents)
   - [Google Antigravity IDE](#google-antigravity-ide)
   - [Claude Desktop](#claude-desktop)
   - [Cursor / VS Code MCP](#cursor--vs-code-mcp)
4. [Multi-File Transactions & Safe Refactoring](#4-multi-file-transactions--safe-refactoring)
5. [Verification & Health Checks](#5-verification--health-checks)
6. [Troubleshooting & Diagnostics](#6-troubleshooting--diagnostics)

---

## 1. System Requirements

- **Operating System:** macOS (Apple Silicon or Intel), POSIX compliant
- **Python:** Python 3.11+ (recommended: Python 3.12 via `uv`)
- **Package Manager:** `uv` installed (`brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **VCS:** `git` initialized in workspaces target files live in

---

## 2. Quick Start & Local Execution

### 2.1 Sync Dependencies

Navigate to the Python implementation directory and run `uv sync`:

```bash
cd implementations/python
uv sync
```

This will automatically create a local virtual environment and install dependencies (`mcp`, `pydantic`, `jsonschema`, `ruff`, `pytest`).

### 2.2 Run the Server Over Stdio

The server communicates via standard input/output (`stdio` JSON-RPC transport):

```bash
# From workspace root:
uv run --directory implementations/python python -m server

# Or directly within implementations/python/:
uv run python -m server
```

The server will initialize quietly on `stdin`/`stdout`, routing all diagnostic logs to `stderr` to preserve protocol message framing.

---

## 3. Connecting CEMP to AI Coding Agents

To enable your coding agent to utilize CEMP, add the server to your agent's MCP configuration.

### Google Antigravity IDE

In your Antigravity IDE configuration (e.g. in `~/.gemini/antigravity-ide/mcp_config.json` or workspace settings):

```json
{
  "mcpServers": {
    "cemp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/<your-username>/dev/CEMP/implementations/python",
        "python",
        "-m",
        "server"
      ]
    }
  }
}
```

### Claude Desktop

In macOS Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "cemp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/Users/<your-username>/dev/CEMP/implementations/python",
        "python",
        "-m",
        "server"
      ]
    }
  }
}
```

### Cursor / VS Code MCP

In `.cursor/mcp.json` or `.vscode/mcp.json`:

```json
{
  "mcpServers": {
    "cemp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "${workspaceFolder}/implementations/python",
        "python",
        "-m",
        "server"
      ]
    }
  }
}
```

---

## 4. Multi-File Transactions & Safe Refactoring

When performing cross-cutting refactoring spanning multiple files, use CEMP atomic multi-file transactions to avoid leaving the codebase in a half-applied state:

### 4.1 Step-by-Step Workflow

1. **Start Transaction**: Call `begin_transaction()` to obtain an isolated `tx_id`.
2. **Propose and Stage Changes**:
   - Call `propose_edit(...)` or `propose_line_edit(...)` to generate patches.
   - Stage each patch via `apply_patch(patch_id=..., tx_id=tx_id)`. The tool returns `status: "staged"` without modifying files on disk.
3. **Batch Commit**:
   - Call `commit_transaction(tx_id=tx_id, verify_syntax=True)`.
   - CEMP validates CAS baseline hashes across all staged files, creates pre-edit Git undo snapshots, writes changes atomically, and validates syntax.
4. **Abort / Rollback (Optional)**:
   - If refactoring is cancelled, call `rollback_transaction(tx_id=tx_id)` to discard staged files and clean up temporary storage.

### 4.2 Error Handling and Recovery

- **`E_TRANSACTION_ACTIVE` (`-32031`)**: Another transaction is already open in the session. Call `commit_transaction` or `rollback_transaction` on the existing transaction before opening a new one.
- **`E_TRANSACTION_NOT_FOUND` (`-32030`)**: The specified `tx_id` is invalid or expired (default TTL: 1800s). Call `begin_transaction` to initiate a fresh session.
- **`E_FILE_MODIFIED` (`-32011`)**: A target file was edited externally between patch creation and commit. Re-inspect the file with `read_file` and re-propose patches against current file state.
- **`E_ROLLBACK_TRIGGERED` (`-32042`)**: Post-write syntax validation failed on one or more files. CEMP has already restored all touched files in the batch to their pre-commit snapshot. Review compiler diagnostics in the error payload to resolve syntax issues.

---

## 5. Verification & Health Checks

Run the automated test suite to verify conformance with protocol schemas and error handling:

```bash
# Run all conformance tests
uv run --directory implementations/python pytest

# Check code quality and style
uv run --directory implementations/python ruff check .
```

To test the live stdio handshake manually from a shell:

```bash
echo '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "manual-test", "version": "1.0.0"}}}' | uv run --directory implementations/python python -m server
```

You should see a single JSON-RPC response on stdout containing `"name": "cemp"` with diagnostic timestamped logs printed to stderr.

---

## 6. Troubleshooting & Diagnostics

### Standard Output Pollution
- **Symptom:** MCP host reports `JSONDecodeError` or unexpected end of input during handshake.
- **Root Cause:** Print statements or library loggers writing unformatted text to `stdout`.
- **Solution:** In CEMP, all logging is strictly routed to `sys.stderr` using `debug_log(...)` in `server_helpers.py`. Ensure any newly added modules use `debug_log(...)` and never call raw `print()`.

### Missing uv in PATH
- **Symptom:** Agent reports `command not found: uv`.
- **Solution:** Provide the absolute path to `uv` (e.g. `/opt/homebrew/bin/uv` or `~/.cargo/bin/uv`) in your MCP configuration file.
