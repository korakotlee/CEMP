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
4. [Verification & Health Checks](#4-verification--health-checks)
5. [Troubleshooting & Diagnostics](#5-troubleshooting--diagnostics)

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

## 4. Verification & Health Checks

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

## 5. Troubleshooting & Diagnostics

### Standard Output Pollution
- **Symptom:** MCP host reports `JSONDecodeError` or unexpected end of input during handshake.
- **Root Cause:** Print statements or library loggers writing unformatted text to `stdout`.
- **Solution:** In CEMP, all logging is strictly routed to `sys.stderr` using `debug_log(...)` in `server.py`. Ensure any newly added modules use `debug_log(...)` and never call raw `print()`.

### Missing uv in PATH
- **Symptom:** Agent reports `command not found: uv`.
- **Solution:** Provide the absolute path to `uv` (e.g. `/opt/homebrew/bin/uv` or `~/.cargo/bin/uv`) in your MCP configuration file.
