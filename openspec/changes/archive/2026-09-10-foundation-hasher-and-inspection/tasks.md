## 1. Hasher and Workspace Boundary Protection (TDD)

- [x] 1.1 Create unit test suite `tests/test_hasher.py` verifying CRLF/LF line ending normalization and deterministic SHA-256 CAS computation. Run with `uv run pytest tests/test_hasher.py` to confirm failure before implementation.
- [x] 1.2 Implement `core/hasher.py` with `normalize_line_endings` and `compute_content_hash` functions, verifying that `tests/test_hasher.py` passes cleanly.
- [x] 1.3 Create workspace boundary unit tests in `tests/test_workspace.py` testing relative and absolute path resolution, directory traversal rejection (`..`), and sensitive directory restrictions (`.git/`, `.env`). Run with `uv run pytest tests/test_workspace.py` to confirm failure before implementation.
- [x] 1.4 Add `PathTraversalError` (-32050), `FileNotFoundCempError` (-32051), `InvalidRangeError` (-32003), and `PermissionDeniedCempError` (-32052) to `errors/system_errors.py`, and implement `core/workspace.py` path validator, verifying `tests/test_workspace.py` passes.

## 2. File Inspection and Search Tools (TDD)

- [x] 2.1 Create comprehensive inspection tests in `tests/test_inspection.py` asserting schema compliance, 1-indexed line formatting, `line_range` boundary checking, optimistic hashing, and regex/literal `search_code` context lines. Run with `uv run pytest tests/test_inspection.py` to confirm failure before implementation.
- [x] 2.2 Implement `core/engine.py` with `read_file`, `get_file_hash`, and `search_code` core functions adhering to schema constraints, verifying unit test logic in `tests/test_inspection.py`.
- [x] 2.3 Wire and export `read_file`, `get_file_hash`, and `search_code` as decorated tools on `server.py`, ensuring all runtime exceptions map to standardized CEMP error payloads.

## 3. Conformance Verification and Documentation

- [x] 3.1 Extend `tests/test_conformance.py` to validate `read_file` and `search_code` responses against `protocol/schemas/read_file.json` and `protocol/schemas/search_code.json` using `jsonschema`. Run `uv run pytest tests/test_conformance.py` to verify conformance.
- [x] 3.2 Run full test suite with `uv run pytest` and linting checks with `uv run ruff check .` to ensure 100% pass and verify all source files are strictly under 300 lines.
- [x] 3.3 Update `README.md` and `implementations/python/README.md` to document the new inspection tool contracts, parameters, and error behavior.
