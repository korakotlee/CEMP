## 1. Test Setup & Defect Replication

- [x] 1.1 Write unit tests for `PatchCache` covering TTL expiration, UUID generation, state transitions, and error codes in `tests/test_patch_cache.py` and verify test failure
- [x] 1.2 Write unit tests for atomic file replacement, `fsync`, and cleanup on write errors in `tests/test_storage.py` and verify test failure
- [x] 1.3 Write unit tests for `propose_edit`, `propose_line_edit`, and `apply_patch` covering occurrence checking, CAS guards, and diff formatting in `tests/test_two_phase_commit.py` and verify test failure

## 2. Core Implementation

- [x] 2.1 Implement `core/patch_cache.py` with `PatchCache`, `PatchProposal` model, and 15-minute TTL eviction, verifying `test_patch_cache.py` passes
- [x] 2.2 Implement `core/storage.py` with sibling temporary file writes, descriptor `fsync`, and atomic `os.replace`, verifying `test_storage.py` passes
- [x] 2.3 Implement `propose_edit` and `propose_line_edit` in `core/engine.py` generating standard `difflib.unified_diff` previews and staging into `PatchCache`
- [x] 2.4 Implement `apply_patch` in `core/engine.py` with CAS pre-condition verification and atomic disk replacement
- [x] 2.5 Mount `propose_edit`, `propose_line_edit`, and `apply_patch` MCP tools onto `server.py`, verifying all tests in `test_two_phase_commit.py` pass

## 3. Conformance & Refactoring

- [x] 3.1 Validate live JSON schema conformance in `tests/test_conformance.py` for `propose_edit.json`, `propose_line_edit.json`, and `apply_patch.json`
- [x] 3.2 Run `ruff check` and verify every source file adheres to the 300-line limit and coding standards, refactoring if necessary
