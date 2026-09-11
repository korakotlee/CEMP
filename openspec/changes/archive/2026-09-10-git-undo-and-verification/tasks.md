## 1. Test Setup & Harness (TDD Foundation)

- [x] 1.1 Add failing unit tests for `GitUndoManager` in `implementations/python/tests/test_git_undo.py` covering git loose blob creation (`git hash-object`), zero commit/reflog pollution, and non-git fallback backups
- [x] 1.2 Add failing unit tests for verification checkers in `implementations/python/tests/test_verification.py` covering Python syntax check (`py_compile`), Node check (`node --check`), and unsupported extension passthrough
- [x] 1.3 Add failing integration and conformance tests in `implementations/python/tests/test_two_phase_commit.py` and `implementations/python/tests/test_conformance.py` for post-write syntax verification, automatic rollback (`E_SYNTAX_ERROR` / `E_ROLLBACK_TRIGGERED`), and `undo_last` tool schema compliance

## 2. Core Implementation: Git Undo Manager

- [x] 2.1 Implement `core/git_undo.py` with `GitUndoManager` supporting `git hash-object -w` blob creation, `git cat-file -p` extraction, in-memory/fallback backups, and LIFO patch history stack
- [x] 2.2 Verify `test_git_undo.py` passes cleanly via `uv run --directory implementations/python pytest tests/test_git_undo.py`


## 3. Core Implementation: Syntax Verification Registry

- [x] 3.1 Implement `verification/registry.py`, `verification/python_checker.py`, and `verification/node_checker.py` returning structured `SyntaxResult` payloads
- [x] 3.2 Verify `test_verification.py` passes cleanly via `uv run --directory implementations/python pytest tests/test_verification.py`


## 4. Integration: Engine & Server Wiring

- [x] 4.1 Update `core/engine.py` to record undo snapshot prior to write, trigger post-write syntax verification, execute auto-rollback on failure, and raise standard error codes
- [x] 4.2 Expose `undo_last` tool in `server.py` conforming to `protocol/schemas/undo_last.json` and update `apply_patch` tool signature to accept `verify_syntax: bool = True`
- [x] 4.3 Verify full integration tests pass via `uv run --directory implementations/python pytest`


## 5. Refactoring & Verification

- [x] 5.1 Refactor any touched source files to strictly maintain the <= 300 lines/file limit
- [x] 5.2 Run code linting via `uv run --directory implementations/python ruff check`
- [x] 5.3 Verify all unit and conformance tests pass cleanly via `uv run --directory implementations/python pytest`

