## Context

See `proposal.md` for motivation and high-level scope.

The CEMP reference implementation currently handles single-file patch proposals (`propose_edit`, `propose_line_edit`), in-memory patch caching (`PatchCache`), atomic single-file replacements (`AtomicStorageManager`), and git blob rollback (`GitUndoManager`) coordinated via `EditingEngine`. Multi-file modifications currently execute as independent, sequential operations. If an operation fails midway through a sequence, the working tree is left in an inconsistent state.

This design introduces multi-file transaction semantics via `TransactionManager` in `core/transactions.py`, integrating with `PatchCache`, `AtomicStorageManager`, and `GitUndoManager` while respecting the repository constraint of keeping all files under 300 lines.

## Goals / Non-Goals

**Goals:**
- Provide atomic multi-file operations (`begin_transaction`, `commit_transaction`, `rollback_transaction`) conforming to `protocol/schemas/transaction.json`.
- Support transactional staging in `apply_patch` with optional `tx_id`, returning status `staged` without touching live files.
- Isolate staged modifications in ephemeral per-transaction directories (`<tempdir>/cemp_tx_<tx_id>/`).
- Enforce Compare-And-Swap (CAS) hash verification across all staged target files before committing any file.
- Guarantee all-or-nothing atomicity during commit: pre-capture undo snapshots, write files atomically, run syntax validation, and automatically roll back all touched files if any verification check fails (`E_ROLLBACK_TRIGGERED` `-32042`).
- Disallow nested or overlapping active transactions per session (`E_TRANSACTION_ACTIVE` `-32031`).
- Prune temporary directories on commit, rollback, and timeout.

**Non-Goals:**
- Distributed two-phase commit coordinators across networked hosts (CEMP is single-host local MCP).
- Crash-durable WAL persistence surviving machine power loss or OS kernel panics.
- Long-lived branched working trees or branching transactions.

## Decisions

### 1. Dedicated `core/transactions.py` Module
- **Decision:** Encapsulate transaction lifecycle, staging management, and batch coordination in `implementations/python/core/transactions.py` instead of expanding `engine.py`.
- **Rationale:** Keeps `core/engine.py` focused on tool coordination and maintains strict adherence to the 300-line file length limit.
- **Alternatives Considered:** Inlining transaction logic directly into `core/engine.py` (rejected due to excessive complexity and file length violation).

### 2. Filesystem-Backed Ephemeral Staging Directory
- **Decision:** Stage modified file contents in an isolated temporary directory per transaction (`tempfile.mkdtemp(prefix="cemp_tx_")`).
- **Rationale:** Staging on disk allows verification checks and diff generators to operate against actual files without modifying the live workspace files. Clean up on commit, rollback, or process exit.
- **Alternatives Considered:** In-memory string buffers only (rejected because multi-file syntax tools and potential future linters expect path-like file accessibility).

### 3. Coordinated Batch Commit with Git Blob Rollback
- **Decision:** Execute commit in distinct coordinated phases:
  1. Pre-commit CAS check: Verify live files match initial proposal SHA-256 hashes. Reject with `E_FILE_MODIFIED` `-32011` if any file drifted.
  2. Undo snapshot capture: Save pre-edit Git blobs for all staged files via `GitUndoManager`.
  3. Atomic writes: Replace each live file with staged content via `AtomicStorageManager`.
  4. Post-write verification: If `verify_syntax` is true, run syntax checks on all modified files.
  5. Rollback on failure: If any file fails verification, restore all modified files from snapshots and return `E_ROLLBACK_TRIGGERED` `-32042`.
  6. Finalize: Mark transaction committed and remove staging directory.
- **Rationale:** Ensures clean all-or-nothing semantics. Any single error aborts or restores the entire set of modified files.
- **Alternatives Considered:** Best-effort partial writes (rejected because partial commits leave broken codebases).

### 4. Single Active Transaction Per Session
- **Decision:** Allow at most one active transaction per server session at any given time.
- **Rationale:** Prevents interleaving lock deadlocks and conforms directly to the protocol error specification (`E_TRANSACTION_ACTIVE` `-32031`).
- **Alternatives Considered:** Concurrent multi-session transactions with file-level read/write locks (deferred to future extensions as unnecessary complexity for current agent usage).

## Risks / Trade-offs

- **[Risk]** Process crash while writing files during batch commit.
  - **Mitigation:** Pre-write Git undo snapshots ensure that the host repository can restore pre-commit states through `undo_last` or standard git inspection.
- **[Risk]** Orphaned temporary directories if an agent abandons a transaction without commit or rollback.
  - **Mitigation:** Transactions include an expiration timestamp (15 minutes TTL). `TransactionManager` prunes expired staging directories during new operations or shutdown.
- **[Risk]** Performance degradation with large multi-file transactions.
  - **Mitigation:** Workload constraint limits batch size to 50 files; batch replacement and hashing use fast local I/O and streaming SHA-256, well within the 200ms target.
