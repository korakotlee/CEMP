**Type:** [x] Feature Request  |  [ ] Bug / Defect  |  [ ] UI / UX  |  [ ] Backend / Performance  |  [ ] External Integration
**Phase:** [ ] 1. Foundation & Tooling  |  [x] 2. Domain Modeling & Core Architecture  |  [ ] 3. Vertical Slice / Tracer Bullet  |  [ ] 4. MVP Feature Buildout  |  [ ] 5. Operational Readiness & Polish  |  [ ] 6. Hardening & Launch

---

### 1. Summary
Implement the two-phase commit (2PC) patch proposal and application engine (`propose_edit`, `propose_line_edit`, and `apply_patch`), supporting exact string matching with strict occurrence enforcement, line-range edits with CAS guards, unified diff generation, and APFS atomic file replacement.

### 2. Context & Problem
* **Current Behavior:** Blind stream edits (`sed`, `awk`) directly touch disk. Ambiguous matches lead to silent multi-line clobbering, race conditions overwrite concurrent edits, and interrupted writes corrupt source files.
* **Expected Behavior:** Edits are proposed and reviewed in memory first without touching disk. Proposing returns a unified diff preview and an ephemeral `patch_id`. Committing requires an explicit `apply_patch` call that re-validates file hashes and performs atomic file replacement.

### 3. Acceptance Criteria
- [x] Implement in-memory `PatchCache` with UUID `patch_id` generation, state tracking, and a 15-minute default Time-To-Live (TTL). Expired patches return error `-32021` (`E_PATCH_EXPIRED`).
- [x] Implement `propose_edit` conforming to `protocol/schemas/propose_edit.json`:
  - Enforce `expected_occurrences` (default: `1`).
  - Return error `-32000` (`E_NO_MATCH`) if occurrence count is 0.
  - Return error `-32001` (`E_OCCURRENCE_MISMATCH`) with line locations of all matches if occurrence count does not equal `expected_occurrences`.
  - Generate standard unified diff preview via standard library `difflib.unified_diff`.
- [x] Implement `propose_line_edit` conforming to `protocol/schemas/propose_line_edit.json`:
  - Validate 1-indexed start and end line ranges against target file length.
  - Validate `content_hash` against live file SHA-256 digest, returning error `-32010` (`E_STALE_HASH`) on mismatch with current hash.
  - Generate unified diff preview and return `patch_id`.
- [x] Implement `core/storage.py` for APFS atomic replacement:
  - Write replacement content to temporary sibling file (`<path>.<uuid>.cemp.tmp`).
  - Flush user-space buffers and call `os.fsync` on the descriptor before renaming.
  - Execute atomic replace using `os.replace`.
- [x] Implement `apply_patch` conforming to `protocol/schemas/apply_patch.json`:
  - Re-verify target file content hash against pre-condition baseline before disk write.
  - Atomically swap modified content into target file.
  - Mark `patch_id` as applied to prevent duplicate execution (raising `-32022` `E_PATCH_ALREADY_APPLIED`).
- [x] Mount tools onto `server.py` and validate live against `tests/test_conformance.py`.

### 4. Data Model
* **Storage & Schema:** Ephemeral in-memory dictionary for `PatchCache` (`patch_id -> PatchProposal(path, base_hash, new_content, diff, created_at, status)`).
* **Transactions & Consistency:** Two-phase commit protocol. Optimistic concurrency control via SHA-256 content hashes (CAS).
* **Lifecycle & Compliance:** Cached patch proposals expire automatically after 15 minutes. Temporary `.cemp.tmp` files are cleaned up in `finally` blocks upon write failure.

### 5. System Architecture
* **Design & Alignment:** Decoupled proposal stage (`engine.py`) and storage commit stage (`storage.py`), registered as tools on `server.py`.
* **Workload & Constraints:** Instant diff generation (<50ms for 5,000 lines); atomic replacement prevents file corruption even under hard process termination.
* **Boundaries & State:** Memory-only during `propose_*`; disk mutation occurs strictly inside `apply_patch`.
* **Tech Stack & Dependencies:** Python 3.11+, `difflib`, `pydantic` v2, `os`, `uuid`, `datetime`.
* **Modularity:** Separate modules for proposal logic (`core/engine.py`), patch caching (`core/patch_cache.py`), and atomic disk writes (`core/storage.py`).

### 6. Reliability & Resilience
* **Known Risks:** Process termination midway through proposal leaves stale entries in cache; concurrent file modification between proposal and apply phases.
* **Concurrency & Synchronization:** CAS pre-condition check inside `apply_patch` immediately detects intervening file modifications (`E_FILE_MODIFIED` / `E_STALE_HASH`).
* **Fault Tolerance & Fallbacks:** If temporary file creation or write fails, target file is untouched; temporary artifacts are unlinked.
* **Blast Radius Containment:** Edits strictly isolated to single target file paths.
* **Observability & Logging:** Structured timestamped debug logs tracking patch lifecycle transitions (`PROPOSED` -> `APPLIED` or `EXPIRED`).

### 7. Technical Context
* **Affected Areas:** `implementations/python/core/engine.py`, `implementations/python/core/storage.py`, `implementations/python/core/patch_cache.py`, `implementations/python/server.py`, `implementations/python/tests/`.
* **Implementation Approach:** Build `PatchCache`, wire `propose_edit` and `propose_line_edit` to generate unified diffs without modifying files, wire `apply_patch` to execute atomic `os.replace`, and mount on `server.py`.
* **Dependencies & Blockers:** Requires Ticket 001 (`server.py` skeleton) and Ticket 002 (hasher and inspection).
* **Refactoring & Reuse:** Uses `hasher.py` for all CAS validations.

### 8. Opportunities & Scope Expansion (Optional)
* **Future Capabilities:** Strategy C (AST-aware patching via `libcst`) can be plugged into this two-phase engine as an additional proposal method.
* **Optimizations:** Memory-efficient chunked diffing for large files.

### 9. Alternatives Considered
* **Alternative:** Direct in-place file editing with regular expressions (like `re.sub`).
* **Tradeoff:** Regex in-place editing provides no dry-run review, lacks occurrence validation, and can corrupt files if invalid regex patterns are passed. Two-phase commit with strict literal matching is chosen for safety.
