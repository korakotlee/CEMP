## Why

Agent code edits frequently introduce syntax errors, broken grammar, or unintended regressions. Traditional agent tooling either leaves broken code on disk or relies on scratch git commits and checkouts that pollute git history and risk corrupting uncommitted developer work. 

This change introduces zero-pollution Git-backed undo snapshots via Git plumbing (`git hash-object`) and automated post-write syntax verification hooks. Broken code is detected and rolled back automatically before the agent completes its turn, and agents gain an explicit `undo_last` tool to safely revert previous edits without git pollution.

## What Changes

- Implement `core/git_undo.py` using Git plumbing (`git hash-object -w`, `git cat-file -p`) for pre-edit snapshots, storing loose blobs in the object store with zero commit or reflog pollution.
- Provide graceful degradation in `core/git_undo.py` for non-git workspaces using temporary filesystem backups.
- Implement `verification/` module with a registry and language syntax checkers:
  - `python_checker.py` using standard library `py_compile.compile`.
  - `node_checker.py` using `node --check` when the Node.js runtime is detected.
- Enhance `apply_patch` in `server.py` and `core/engine.py` to:
  - Snapshot target file state prior to write using `git_undo`.
  - Execute syntax verification immediately following atomic write.
  - Automatically roll back file contents and raise `E_SYNTAX_ERROR` (`-32040`) or `E_ROLLBACK_TRIGGERED` (`-32042`) if syntax validation fails.
  - Return syntax check details in the response when verification succeeds.
- Expose `undo_last` tool on `server.py` conforming to `protocol/schemas/undo_last.json` to revert recent patches cleanly.

## Capabilities

### New Capabilities
- `undo`: Zero-pollution Git-backed file state preservation, patch history tracking, and the `undo_last` tool for reverting applied patches without committing or altering git references.

### Modified Capabilities
- `two-phase-commit`: Extend `apply_patch` to incorporate pre-write snapshotting, optional post-write syntax verification (`verify_syntax`), automatic rollback on validation failure, and diagnostic reporting.

## Impact

- `implementations/python/server.py`: Mount `undo_last` tool and update `apply_patch` signature and error handling.
- `implementations/python/core/engine.py`: Integrate pre-write undo snapshotting and post-write verification hooks.
- `implementations/python/core/git_undo.py`: New module for Git plumbing snapshot and rollback management.
- `implementations/python/verification/`: New module for syntax checker registry and language-specific checkers.
- `protocol/schemas/`: Validated against existing `undo_last.json`, `syntax_check.json`, and `apply_patch.json`.
- Zero new external runtime dependencies; uses Python standard library (`subprocess`, `py_compile`) and existing dev dependencies.
