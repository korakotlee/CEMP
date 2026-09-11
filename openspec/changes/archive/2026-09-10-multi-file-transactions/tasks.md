## 1. Test Suite Preparation (TDD Red Phase)

- [x] 1.1 Create `implementations/python/tests/test_transactions.py` with failing test cases for transaction lifecycle (`begin_transaction`, active session duplicate rejection `E_TRANSACTION_ACTIVE` `-32031`, and non-existent transaction `E_TRANSACTION_NOT_FOUND` `-32030`) and verify tests fail with pytest
- [x] 1.2 Add failing test cases in `implementations/python/tests/test_transactions.py` for transactional staging via `apply_patch(patch_id, tx_id)` returning status `staged` without modifying live files and verify tests fail with pytest
- [x] 1.3 Add failing test cases in `implementations/python/tests/test_transactions.py` for coordinated batch commit in `commit_transaction` (CAS drift abort `E_FILE_MODIFIED` `-32011`, atomic batch replacement, and automatic batch rollback on syntax failure `E_ROLLBACK_TRIGGERED` `-32042`) and verify tests fail with pytest
- [x] 1.4 Add failing test cases in `implementations/python/tests/test_transactions.py` for `rollback_transaction` ensuring staging directory cleanup and working tree preservation, and verify tests fail with pytest

## 2. Core Transaction Manager Implementation (Green Phase)

- [x] 2.1 Implement `implementations/python/core/transactions.py` defining `Transaction` and `TransactionManager` with isolated directory staging (`cemp_tx_<tx_id>`), TTL expiration, and single-transaction session lock, keeping file under 300 lines
- [x] 2.2 Update `implementations/python/core/engine.py` to expose `begin_transaction`, route `apply_patch` with `tx_id` to transaction staging, and delegate commit/rollback to `TransactionManager`
- [x] 2.3 Implement multi-file commit coordination in `core/transactions.py` orchestrating CAS hash verification, pre-edit Git blob capture via `GitUndoManager`, atomic disk replacement via `AtomicStorageManager`, and post-write syntax verification with rollback
- [x] 2.4 Verify all unit tests in `implementations/python/tests/test_transactions.py` pass with `uv run --directory implementations/python pytest implementations/python/tests/test_transactions.py`

## 3. FastMCP Server Integration & Protocol Conformance

- [x] 3.1 Mount `begin_transaction`, `commit_transaction`, and `rollback_transaction` MCP tools onto `implementations/python/server.py`
- [x] 3.2 Update `apply_patch` MCP tool parameter signature and response model in `implementations/python/server.py` to accept optional `tx_id`
- [x] 3.3 Add schema conformance test cases to `implementations/python/tests/test_conformance.py` validating tool responses against `protocol/schemas/transaction.json` and `protocol/schemas/apply_patch.json`
- [x] 3.4 Run full test suite with `uv run --directory implementations/python pytest` and verify 100% passing tests

## 4. Refactoring, Linting & Documentation

- [x] 4.1 Run `uv run --directory implementations/python ruff check` and resolve any lint or formatting warnings
- [x] 4.2 Verify all source files (`core/transactions.py`, `core/engine.py`, `server.py`) strictly adhere to the 300-line ceiling
- [x] 4.3 Update `README.md` and `docs/` with multi-file transaction usage examples and error handling instructions
