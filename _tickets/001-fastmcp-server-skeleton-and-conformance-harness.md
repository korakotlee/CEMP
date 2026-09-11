**Type:** [x] Feature Request  |  [ ] Bug / Defect  |  [ ] UI / UX  |  [x] Backend / Performance  |  [x] External Integration
**Phase:** [x] 1. Foundation & Tooling  |  [ ] 2. Domain Modeling & Core Architecture  |  [ ] 3. Vertical Slice / Tracer Bullet  |  [ ] 4. MVP Feature Buildout  |  [ ] 5. Operational Readiness & Polish  |  [ ] 6. Hardening & Launch

---

### 1. Summary
Establish the executable "walking skeleton" of the CEMP Python implementation by creating `server.py` with FastMCP stdio transport, standardized JSON-RPC error handling, and a schema-driven test harness (`tests/test_conformance.py`) so every tool can be mounted and tested live as it is developed.

### 2. Context & Problem
* **Current Behavior:** Without an early server skeleton and test harness, domain modules (`hasher`, `engine`, `storage`) are developed in isolation with mocked unit tests, deferring integration and schema validation to the very end of the project.
* **Expected Behavior:** An immediate running server harness exists from Day 1. Developers can run `uv run python -m server`, connect MCP hosts, and run `pytest tests/test_conformance.py` to continuously validate tool signatures and responses against `protocol/schemas/*.json` as each feature is completed.

### 3. Acceptance Criteria
- [ ] Scaffold `implementations/python/pyproject.toml` with `mcp[cli]>=1.2.0`, `pydantic>=2.0`, `jsonschema>=4.20`, `ruff`, and `pytest`.
- [ ] Create `implementations/python/server.py` initializing the FastMCP server instance:
  - Configure server name `cemp` and version `1.0.0-draft`.
  - Expose stdio transport as default entrypoint (`uv run python -m server`).
  - Add centralized exception handler converting internal exceptions to standardized CEMP error payloads matching `protocol/error-codes.md`.
- [ ] Implement `tests/conftest.py` with reusable fixtures:
  - Isolated temporary git repository fixture (`temp_git_repo`).
  - FastMCP client test runner fixture for invoking tools in-memory over stdio pipes.
  - JSON schema validator fixture loading schemas from `protocol/schemas/`.
- [ ] Implement `tests/test_conformance.py`:
  - Verify server boots up cleanly and handles invalid tool arguments with schema validation errors.
  - Verify error formatting includes `code`, `name`, `message`, `data`, `recoverable`, and `suggested_action`.
- [ ] Ensure formatting and quality checks pass (`ruff check`, `ruff format --check`).

### 4. Data Model
* **Storage & Schema:** MCP JSON-RPC 2.0 protocol over stdio. Schema fixtures load JSON Schema Draft 2020-12 specifications dynamically from `protocol/schemas/*.json`.
* **Transactions & Consistency:** Server lifecycle manages session-level context for upcoming transaction managers.
* **Lifecycle & Compliance:** Graceful shutdown on SIGINT/SIGTERM. Stdio streams reserved strictly for JSON-RPC messages; all debug logging directed to stderr.

### 5. System Architecture
* **Design & Alignment:** Walking Skeleton (Tracer Bullet) pattern. Decouples the MCP transport adapter layer (`server.py`) from domain business logic (`core/`).
* **Workload & Constraints:** Zero-latency stdio communication. Immediate response to host initialization handshake.
* **Boundaries & State:** `server.py` serves as the outer entrypoint and routing facade.
* **Tech Stack & Dependencies:** Python 3.11+, `FastMCP` (`mcp[cli]`), `pydantic` v2, `jsonschema`, `pytest`.
* **Modularity:** Kept under 150 lines; delegating actual tool implementations to `core/` as they arrive.

### 6. Reliability & Resilience
* **Known Risks:** Standard output pollution from print statements or third-party libraries corrupting JSON-RPC framing.
* **Concurrency & Synchronization:** Async event loop with per-session connection state.
* **Fault Tolerance & Fallbacks:** Uncaught exceptions caught at server boundary and converted into JSON-RPC error objects rather than crashing the transport process.
* **Blast Radius Containment:** Server process runs with local user permissions, scoped to explicit workspace directories.
* **Observability & Logging:** Structured timestamped debug logging routed strictly to `sys.stderr`.

### 7. Technical Context
* **Affected Areas:** `implementations/python/pyproject.toml`, `implementations/python/server.py`, `implementations/python/tests/conftest.py`, `implementations/python/tests/test_conformance.py`.
* **Implementation Approach:** Scaffold `pyproject.toml`, create minimal `FastMCP("cemp")`, set up `tests/conftest.py` with in-memory client and schema validator, and write baseline conformance tests.
* **Dependencies & Blockers:** None. This ticket is the foundational walking skeleton for all subsequent tickets.
* **Refactoring & Reuse:** The test fixtures in `conftest.py` and conformance validator will be reused by every subsequent tool ticket.

### 8. Opportunities & Scope Expansion (Optional)
* **Future Capabilities:** Adding Server-Sent Events (SSE) or Unix socket transport modes for daemonized operation.
* **Optimizations:** Pre-compiling JSON schema validators on test fixture initialization.

### 9. Alternatives Considered
* **Alternative:** Building all core domain logic first and wiring `server.py` at the very end.
* **Tradeoff:** Deferring server assembly makes it impossible to test tools through the actual MCP transport during development and increases integration risk. The walking skeleton approach enables continuous end-to-end verification.
