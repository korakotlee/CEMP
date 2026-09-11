**Type:** [x] Feature Request  |  [ ] Bug / Defect  |  [ ] UI / UX  |  [ ] Backend / Performance  |  [ ] External Integration
**Phase:** [ ] 1. Foundation & Tooling  |  [ ] 2. Domain Modeling & Core Architecture  |  [ ] 3. Vertical Slice / Tracer Bullet  |  [x] 4. MVP Feature Buildout  |  [ ] 5. Operational Readiness & Polish  |  [ ] 6. Hardening & Launch

---

### 1. Summary
Implement multi-file transaction management (`begin_transaction`, `commit_transaction`, and `rollback_transaction`), enabling atomic, all-or-nothing multi-file refactoring without leaving half-applied or inconsistent codebase states.

### 2. Context & Problem
* **Current Behavior:** Complex refactorings span multiple files. If an agent edits 4 out of 5 files successfully but the 5th file fails, the codebase is left in a broken, half-applied state that breaks build pipelines and test suites.
* **Expected Behavior:** An agent can begin a transaction (`tx_id`), stage multiple patch proposals against that transaction, and commit them atomically. If any file in the batch fails hash verification or syntax checking, none of the files are written to disk, or all staged modifications are rolled back atomically.

### 3. Acceptance Criteria
- [ ] Implement `core/transactions.py` managing transaction lifecycles and staged patch registries.
- [ ] Implement `begin_transaction` conforming to `protocol/schemas/transaction.json`:
  - Generate a cryptographically secure `tx_id`.
  - Disallow nested or overlapping concurrent transactions per session, raising error `-32031` (`E_TRANSACTION_ACTIVE`).
- [ ] Extend `apply_patch(patch_id, tx_id)`:
  - If `tx_id` is supplied, validate `tx_id` exists (otherwise raise `-32030` `E_TRANSACTION_NOT_FOUND`).
  - Stage the patch in an isolated temporary staging directory or memory map instead of modifying the live file immediately.
  - Return staging confirmation with staged file list.
- [ ] Implement `commit_transaction(tx_id)`:
  - Verify all target files still match their pre-condition CAS hashes. If any file has drifted, abort commit with `-32011` (`E_FILE_MODIFIED`).
  - Capture pre-edit Git blobs for all target files in the transaction batch.
  - Apply atomic file replacements across all files in coordinated sequence.
  - Execute post-write verification across all modified files.
  - If any verification check fails, automatically rollback all files modified in the transaction batch and raise `-32042` (`E_ROLLBACK_TRIGGERED`).
  - Return list of successfully updated files and commit status.
- [ ] Implement `rollback_transaction(tx_id)`:
  - Discard all staged patches and clean up temporary staging artifacts.
  - Return confirmation of rollback without touching target filesystem.
- [ ] Mount transaction tools on `server.py` and validate against `tests/test_conformance.py` and `tests/test_transactions.py`.

### 4. Data Model
* **Storage & Schema:** Isolated temporary staging workspace (`<tempdir>/cemp_tx_<tx_id>/`) holding candidate file contents. In-memory `Transaction` model tracking active state, target paths, and staged patches.
* **Transactions & Consistency:** Strict ACID-like atomicity and consistency for multi-file operations. All-or-nothing commit guarantee.
* **Lifecycle & Compliance:** Transactions automatically time out after 15 minutes of inactivity; staging directories are pruned on commit, rollback, or timeout.

### 5. System Architecture
* **Design & Alignment:** Staged working tree overlay model in `core/transactions.py`, registered on `server.py`.
* **Workload & Constraints:** Support transactions with up to 50 files; batch commit execution within 200ms.
* **Boundaries & State:** State is isolated within the transaction context until explicit commit invocation.
* **Tech Stack & Dependencies:** Python 3.11+, `pathlib`, `tempfile`, `shutil`, `pydantic` v2.
* **Modularity:** Isolated in `core/transactions.py` with clean hooks into `storage.py` and `git_undo.py`.

### 6. Reliability & Resilience
* **Known Risks:** Process crash while multi-file transaction is half-swapped; stale staging data accumulation.
* **Concurrency & Synchronization:** Target file conflict checking prevents concurrent transactions from modifying overlapping files (`-32032` `E_TRANSACTION_CONFLICT`).
* **Fault Tolerance & Fallbacks:** If a swap fails midway through a batch commit, `GitUndoManager` restores all previously swapped files in reverse order.
* **Blast Radius Containment:** Staged files live in temporary storage; failed commits cannot corrupt existing working tree files.
* **Observability & Logging:** Structured timestamped debug logs tracking transaction milestones (`BEGIN`, `STAGE_PATCH`, `PRE_COMMIT_VERIFY`, `COMMIT_SUCCESS`, `ROLLBACK`).

### 7. Technical Context
* **Affected Areas:** `implementations/python/core/transactions.py`, `implementations/python/server.py`, `implementations/python/tests/test_transactions.py`.
* **Implementation Approach:** Create `TransactionManager`, support staging directories, orchestrate two-phase batch commit with rollback safety nets, and mount on `server.py`.
* **Dependencies & Blockers:** Requires Tickets 001, 002, 003, and 004.
* **Refactoring & Reuse:** Reuses `storage.py` atomic replace and `git_undo.py` blob recovery.

### 8. Opportunities & Scope Expansion (Optional)
* **Future Capabilities:** Isolated reference namespace snapshots (`refs/cemp/tx/<tx_id>`) for multi-step transactions surviving process restarts.
* **Optimizations:** APFS copy-on-write file clones (`os.copyfile_range` / `clonefile`) for instantaneous staging of large files.

### 9. Alternatives Considered
* **Alternative:** Sequential uncommitted file edits without transaction staging.
* **Tradeoff:** Sequential direct edits leave partial changes on disk if any subsequent edit fails. Transactional staging guarantees all-or-nothing safety.
