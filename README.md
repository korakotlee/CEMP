# CEMP (Code Editing MCP Protocol)

An open, versioned specification for reliable LLM code editing, paired with a provider-agnostic macOS reference implementation in Python.

---

## The Problem

AI coding agents commonly rely on raw text-stream utilities like `grep`, `sed`, and `awk` for code modifications. These tools suffer from severe failure modes:

- **Silent mis-edits**: Line-based regex replacement silently mutates the wrong occurrence when patterns are ambiguous.
- **No preview phase**: Mutations happen directly on disk with no dry-run or diff verification stage.
- **Race conditions**: Files modified by users or background builders between read and edit get clobbered without optimistic concurrency controls.
- **Platform footguns**: Incompatible flags and regex dialects between macOS BSD tools (`sed -i ''`) and Linux GNU tools cause agents to break environments.
- **No syntax safety net**: Broken syntax is written directly to disk without verification or automatic rollback.

CEMP solves this by defining an open protocol that standardizes safe code editing contracts and guarantees.

---

## Repository Architecture

The project is structured into two core directories:

```text
koutil/
├── protocol/                      # Tech-agnostic reference specification
│   ├── schemas/                   # JSON Schema / OpenAPI tool contracts
│   ├── behavioral-contracts.md    # Guarantees (occurrence counts, CAS, diff previews)
│   └── test-suite/                # Language-agnostic conformance test definitions
├── implementations/
│   └── gemini-python/             # Provider-agnostic macOS Python reference implementation
│       ├── server.py              # FastMCP server entrypoint
│       ├── core/                  # Safe edit engine (diffing, CAS, APFS atomic replace)
│       ├── verification/          # Syntax verification hooks (py_compile, node --check)
│       └── tests/                 # pytest test suite & conformance validator
├── docs/                          # Guides, design records, and idea documents
│   ├── ideas/koutil-protocol.md   # Architectural genesis and roadmap
│   ├── technical-guide.md         # Detailed developer guide
│   └── user-guide.md              # Setup and agent configuration manual
├── AGENTS.md                      # Operational rules and coding invariants for AI agents
├── CHANGELOG.md                   # Release history
└── README.md                      # Project overview
```

### System Architecture

```mermaid
flowchart TD
    subgraph Host ["Agent / LLM Host"]
        Agent["AI Agent (Gemini, Claude, Antigravity, Custom)"]
    end

    subgraph CEMP ["CEMP Architecture"]
        Spec["protocol/<br/>Open Protocol Spec & Schemas"]
        Impl["implementations/gemini-python/<br/>macOS Reference Server"]
    end

    subgraph System ["Target Environment"]
        FS["macOS Filesystem (APFS Atomic os.replace)"]
        Git["Git Repository (Undo & Rollback Backbone)"]
        Syntax["Syntax Checker (py_compile, node --check)"]
    end

    Agent -->|"1. propose_edit (exact match, hash)"| Impl
    Impl -->|"2. diff preview + patch_id"| Agent
    Agent -->|"3. apply_patch(patch_id)"| Impl
    Impl -->|"Two-Phase Commit"| FS
    Impl -->|"Verify Syntax"| Syntax
    Impl -->|"Auto-Rollback on Failure"| Git
    Spec -.->|"Defines Contract & Conformance"| Impl
```

---

## Two-Phase Commit Pattern

Instead of immediate in-place mutation, CEMP decouples edit proposal from disk commit:

1. **`read_file(path, line_range?)`**: Returns content with line numbers and a SHA-256 content hash.
2. **`propose_edit(path, old_str, new_str, expected_occurrences=1)`**:
   - Matches `old_str` with strict occurrence checks.
   - Computes a unified diff preview using Python `difflib`.
   - Returns a preview and an ephemeral `patch_id` without touching disk.
3. **`apply_patch(patch_id)`**:
   - Validates that the file hash has not changed (Compare-And-Swap guard).
   - Writes atomically to disk via `os.replace()` on APFS.
   - Runs syntax validation (`py_compile`, `node --check`).
   - Automatically rolls back if syntax fails.
4. **`undo_last(path)`**: Reverts the last patch using git as the transaction backbone.

---

## Why CEMP Beats sed/awk

| Failure Mode | sed / awk / grep | CEMP Protocol Guarantee |
|---|---|---|
| Ambiguous matches | Silently edits wrong line or all occurrences | Strict `expected_occurrences` enforcement (fails loudly) |
| Blind writes | Writes directly to disk | Two-phase commit: unified diff preview before write |
| Concurrent drift | Silent clobbering | Content-hash compare-and-swap guard |
| Broken syntax | Leaves broken code on disk | Post-apply syntax hooks with automatic rollback |
| Platform differences | BSD `sed` vs GNU `sed` incompatibility | Provider-agnostic, stdlib-backed Python execution |
| Partial refactors | Multi-file edits left half-applied on error | Git-backed undo and atomic file replacement |

---

## Getting Started

### Prerequisites
- macOS (tested on macOS 14 Sonoma and macOS 15 Sequoia)
- Python 3.11+
- `git` installed and initialized in target repositories

### Installation & Local Run

```bash
# Clone the repository
git clone https://github.com/korakot/koutil.git
cd koutil

# Run reference server via uv
uv run --directory implementations/gemini-python python -m server
```

### Agent Host Configuration (MCP)

Add the reference server to your MCP host configuration (e.g. Claude Desktop, Antigravity, Gemini agent harnesses):

```json
{
  "mcpServers": {
    "cemp": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/koutil/implementations/gemini-python",
        "python",
        "-m",
        "server"
      ]
    }
  }
}
```

---

## Verification & Conformance

Verify that the reference implementation conforms to the protocol specification:

```bash
# Run tests
pytest implementations/gemini-python/tests/
```

---

## Documentation & References

- [Protocol Idea & Roadmap](docs/ideas/koutil-protocol.md): Background reasoning and architecture motivations.
- [Technical Guide](docs/technical-guide.md): Deep dive into protocol contracts and atomic write mechanics.
- [User Guide](docs/user-guide.md): Setup, configuration, and agent integration recipes.
- [Agent Guidelines](AGENTS.md): Operational rules, coding standards, and repository invariants.
