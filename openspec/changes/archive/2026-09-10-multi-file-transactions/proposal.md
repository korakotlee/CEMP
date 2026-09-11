## Why

Complex refactorings and cross-cutting architectural changes frequently span multiple files. When edits are applied sequentially without transactional guarantees, a failure or validation error midway through leaves the codebase in a broken, half-applied state that can break builds, disrupt test pipelines, and require tedious manual cleanup. Implementing multi-file transaction management (`begin_transaction`, `commit_transaction`, `rollback_transaction`, and transactional staging in `apply_patch`) ensures atomic, all-or-nothing multi-file modifications with automatic rollback on failure.

## What Changes

- Introduce `begin_transaction`: Opens an atomic multi-file transaction, generating a cryptographically secure `tx_id` with an active TTL and enforcing single active transaction semantics per session (rejecting with `E_TRANSACTION_ACTIVE` `-32031` if another transaction is open).
- Extend `apply_patch`: Adds optional `tx_id` argument to stage proposed patches into an isolated staging overlay instead of writing to disk immediately, returning status `staged`. Validates transaction existence (`E_TRANSACTION_NOT_FOUND` `-32030`).
- Introduce `commit_transaction`: Verifies pre-condition CAS hashes for all staged files (`E_FILE_MODIFIED` `-32011` on drift), captures pre-edit Git blobs for undo snapshots, performs coordinated atomic file replacements across all staged files, executes post-write syntax verification, and automatically rolls back all touched files if any verification check fails (`E_ROLLBACK_TRIGGERED` `-32042`).
- Introduce `rollback_transaction`: Aborts an active transaction and cleans up staged overlays and cached state without altering the target codebase files.
- Mount new MCP tools on `server.py`: `begin_transaction`, `commit_transaction`, and `rollback_transaction`.

## Capabilities

### New Capabilities
- `multi-file-transactions`: Transaction lifecycle management (`begin_transaction`, `commit_transaction`, `rollback_transaction`), isolated multi-file patch staging, coordinated batch atomic commit with rollback safety nets, and collision detection.

### Modified Capabilities
- `two-phase-commit`: Extends `apply_patch` to accept an optional `tx_id` parameter to stage patches inside an open transaction instead of committing directly to disk.

## Impact

- Affected core modules: `implementations/python/core/transactions.py` (new), `implementations/python/core/engine.py` (integrate staging and transaction coordination), `implementations/python/server.py` (mount tools).
- Schema validation: `protocol/schemas/transaction.json` and `protocol/schemas/apply_patch.json`.
- Testing: Conformance suite in `implementations/python/tests/test_conformance.py` and dedicated unit tests in `implementations/python/tests/test_transactions.py`.
