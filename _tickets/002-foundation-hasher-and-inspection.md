**Type:** [x] Feature Request  |  [ ] Bug / Defect  |  [ ] UI / UX  |  [ ] Backend / Performance  |  [ ] External Integration
**Phase:** [x] 1. Foundation & Tooling  |  [ ] 2. Domain Modeling & Core Architecture  |  [ ] 3. Vertical Slice / Tracer Bullet  |  [ ] 4. MVP Feature Buildout  |  [ ] 5. Operational Readiness & Polish  |  [ ] 6. Hardening & Launch

---

### 1. Summary
Implement the SHA-256 CAS hasher and inspection tools (`read_file`, `get_file_hash`, and `search_code`) in `core/engine.py`, mount them onto the FastMCP server, and validate against `protocol/schemas/*.json`.

### 2. Context & Problem
* **Current Behavior:** Agents editing code lack deterministic inspection tools, suffering from off-by-one line indexing errors and blind pattern guessing without ground-truth content hashes.
* **Expected Behavior:** Fast, deterministic inspection utilities registered directly on the FastMCP server. Files can be read with 1-indexed lines and verified with SHA-256 digests, with all outputs validated live against the CEMP conformance suite.

### 3. Acceptance Criteria
- [ ] Implement `core/hasher.py` to compute consistent SHA-256 digests with normalized line endings (`\r\n` to `\n`).
- [ ] Implement `read_file` in `core/engine.py` and register as `@mcp.tool()` on `server.py`:
  - 1-indexed lines formatted as `[line_number, line_content]`.
  - Optional `line_range` parameter with boundary validation.
  - Returns `content_hash` and `total_lines` conforming to `protocol/schemas/read_file.json`.
  - Rejection of out-of-bounds line ranges with error code `-32003` (`E_INVALID_RANGE`).
- [ ] Implement and register `get_file_hash` returning optimistic SHA-256 CAS baseline.
- [ ] Implement and register `search_code` conforming to `protocol/schemas/search_code.json`:
  - Support literal search and regex search with `context_lines`.
  - Path glob filtering across repository workspaces.
- [ ] Implement workspace boundary guard raising error code `-32050` (`E_PATH_TRAVERSAL`) when paths attempt to escape the designated workspace.
- [ ] Validate end-to-end against `tests/test_conformance.py` and unit tests in `tests/test_inspection.py` with 100% pass rate.

### 4. Data Model
* **Storage & Schema:** Read-only direct filesystem inspection. Return payloads conform strictly to JSON Schema definitions in `protocol/schemas/read_file.json` and `protocol/schemas/search_code.json`.
* **Transactions & Consistency:** Establishes CAS baseline hashes for downstream two-phase commit operations.
* **Lifecycle & Compliance:** Strict workspace boundary enforcement; read operations on `.git/` internal databases and sensitive files (`.env`) are restricted.

### 5. System Architecture
* **Design & Alignment:** Standard library Python (`pathlib`, `hashlib`, `re`, `fnmatch`) encapsulated in `core/`, exposed via `@mcp.tool()` decorators in `server.py`.
* **Workload & Constraints:** Sub-millisecond hash calculation and inspection for files up to 10MB; memory-efficient line iteration.
* **Boundaries & State:** Stateless read engine; pure functions where practical.
* **Tech Stack & Dependencies:** Python 3.11+, `pydantic` v2, `pathlib`, `pytest`, `ruff`.
* **Modularity:** Isolated in `core/hasher.py` and `core/engine.py`.

### 6. Reliability & Resilience
* **Known Risks:** Path traversal attacks (`../../etc/passwd`), symlink loops, reading non-existent or binary files.
* **Concurrency & Synchronization:** Safe concurrent reads via non-blocking OS file descriptors.
* **Fault Tolerance & Fallbacks:** Graceful handling of non-UTF8 binary files and missing file paths returning standardized error `E_FILE_NOT_FOUND` (`-32051`).
* **Blast Radius Containment:** Read operations cannot mutate files on disk.
* **Observability & Logging:** Structured timestamped debug logging for file inspection durations and errors.

### 7. Technical Context
* **Affected Areas:** `implementations/python/core/hasher.py`, `implementations/python/core/engine.py`, `implementations/python/server.py`, `implementations/python/tests/test_inspection.py`.
* **Implementation Approach:** Implement normalization and hashing in `hasher.py`, inspection functions in `engine.py`, mount onto `server.py`, and run against the conformance test runner from Ticket 001.
* **Dependencies & Blockers:** Requires Ticket 001 (`server.py` skeleton and test harness).
* **Refactoring & Reuse:** Hasher and boundary validation will be reused by all mutation tools.

### 8. Opportunities & Scope Expansion (Optional)
* **Future Capabilities:** Caching computed file hashes with file mtime validation for rapid incremental lookups.
* **Optimizations:** Memory-mapped I/O (`mmap`) for ultra-fast reading and hashing of large files.

### 9. Alternatives Considered
* **Alternative:** Calling external `ripgrep` via subprocess for `search_code`.
* **Tradeoff:** Adding external binary dependencies complicates installation and cross-platform portability. Python standard library regex and line iteration provide excellent speed without external binary dependencies.
