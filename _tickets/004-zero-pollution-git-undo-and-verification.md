**Type:** [x] Feature Request  |  [ ] Bug / Defect  |  [ ] UI / UX  |  [ ] Backend / Performance  |  [ ] External Integration
**Phase:** [ ] 1. Foundation & Tooling  |  [ ] 2. Domain Modeling & Core Architecture  |  [x] 3. Vertical Slice / Tracer Bullet  |  [ ] 4. MVP Feature Buildout  |  [ ] 5. Operational Readiness & Polish  |  [ ] 6. Hardening & Launch

---

### 1. Summary
Implement zero-pollution Git-backed undo mechanics and automated post-write syntax verification hooks with automatic rollback, ensuring broken code is never left on disk.

### 2. Context & Problem
* **Current Behavior:** Agent code edits frequently introduce syntax errors or broken grammar. Traditional agents have no clean rollback mechanism without creating scratch git commits, corrupting git history, or accidentally wiping out uncommitted developer work.
* **Expected Behavior:** Before writing any patch to disk, the server stores the pre-edit file state as a loose Git blob (`git hash-object -w`). Immediately after write, language-specific syntax checkers (`py_compile`, `node --check`) validate the file. If syntax validation fails, the server automatically rolls back the file from the loose Git blob and returns compiler diagnostics to the agent. `undo_last` provides explicit agent-triggered reversion.

### 3. Acceptance Criteria
- [ ] Implement `core/git_undo.py` leveraging low-level Git plumbing commands via `subprocess`:
  - Capture pre-edit file state into Git object store: `git hash-object -w <path>`.
  - Store object ID in ephemeral patch record.
  - Revert file to pre-edit state: `git cat-file -p <object_id>` piped into temporary sibling file, followed by atomic `os.replace`.
  - Enforce zero commit pollution: No `git commit`, `git checkout`, or modifications to `HEAD` or reflog.
  - Graceful degradation if target is not inside a Git repository (in-memory byte buffer backup).
- [ ] Implement `verification/registry.py` and language checkers:
  - `python_checker.py`: Executes standard library `py_compile.compile(..., doraise=True)`.
  - `node_checker.py`: Executes `node --check <path>` when Node runtime is detected.
- [ ] Wire automated verification into `apply_patch`:
  - Run syntax check immediately following atomic file replacement.
  - If syntax validation passes, return success payload with post-edit content hash.
  - If syntax validation fails, immediately invoke `git_undo` rollback, restoration of original file bytes, and raise error `-32040` (`E_SYNTAX_ERROR`) or `-32042` (`E_ROLLBACK_TRIGGERED`) containing compiler stderr output.
- [ ] Implement and mount `undo_last` tool on `server.py` conforming to `protocol/schemas/undo_last.json`:
  - Revert target file (or globally most recent patch if `path` is omitted).
  - Return reverted patch ID, target path, and restored file hash.
  - Raise `-32060` (`E_UNDO_UNAVAILABLE`) if no prior patch exists.
- [ ] Validate end-to-end against `tests/test_conformance.py` and `tests/test_verification.py`.

### 4. Data Model
* **Storage & Schema:** Git object database (`.git/objects/??/*`) for content-addressed immutable pre-edit file blobs. In-memory stack of applied patch descriptors for `undo_last`.
* **Transactions & Consistency:** Pre-write snapshot guarantees 100% reversible state regardless of verification outcome.
* **Lifecycle & Compliance:** Loose Git blobs are automatically pruned during periodic `git gc` cycles without polluting developer working trees.

### 5. System Architecture
* **Design & Alignment:** Subprocess-based Git plumbing and pluggable language syntax verification registry.
* **Workload & Constraints:** Sub-10ms syntax checking (`py_compile` is sub-millisecond; `git hash-object` executes in <5ms).
* **Boundaries & State:** Interacts with local `.git/objects` directly; does not alter Git index or HEAD reference.
* **Tech Stack & Dependencies:** Python 3.11+, `subprocess`, standard library `py_compile`, Node.js CLI (optional).
* **Modularity:** Isolated in `core/git_undo.py` and `verification/`.

### 6. Reliability & Resilience
* **Known Risks:** Working tree file was dirty prior to edit; `git` CLI not installed or path not a git repository.
* **Concurrency & Synchronization:** Git object hashes are cryptographically unique and content-addressed; concurrent edits do not collide in object storage.
* **Fault Tolerance & Fallbacks:** Fall back to filesystem backup copy (`.cemp.bak`) if directory is not a Git repository.
* **Blast Radius Containment:** Auto-rollback isolates broken code to the specific tool invocation, preventing syntax breakage from poisoning downstream agent turns.
* **Observability & Logging:** Structured timestamped debug logs capturing verification execution time, syntax check results, and rollback executions.

### 7. Technical Context
* **Affected Areas:** `implementations/python/core/git_undo.py`, `implementations/python/verification/`, `implementations/python/server.py`, `implementations/python/tests/`.
* **Implementation Approach:** Implement `GitUndoManager`, build verification registry, wrap `apply_patch` in a verification-and-rollback guard, and mount `undo_last` on `server.py`.
* **Dependencies & Blockers:** Requires Ticket 001, Ticket 002, and Ticket 003.
* **Refactoring & Reuse:** Shared atomic replacement logic in `storage.py` is utilized for restoring blobs.

### 8. Opportunities & Scope Expansion (Optional)
* **Future Capabilities:** Adding TypeScript verification (`tsc --noEmit`), Rust (`cargo check`), or Go (`go vet`).
* **Optimizations:** Running syntax checking asynchronously in thread pools for large projects.

### 9. Alternatives Considered
* **Alternative:** Using `git stash push` and `git stash pop`.
* **Tradeoff:** Stash operations can fail with merge conflicts, modify the developer's stash index, and produce unresolved conflict markers on disk. Git loose blob storage (`hash-object`) is non-destructive and collision-free.
