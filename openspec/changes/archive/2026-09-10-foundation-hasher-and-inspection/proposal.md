## Why

AI agents editing code require deterministic file inspection tools to eliminate off-by-one line indexing errors, blind search guesses, and stale write collisions. Introducing a SHA-256 content-addressable storage (CAS) hasher and standardized inspection tools (`read_file`, `get_file_hash`, `search_code`) enables deterministic inspection, workspace boundary enforcement, and optimistic concurrency baselines for subsequent edits.

## What Changes

- Implement normalized SHA-256 content hashing in `core/hasher.py` to establish CAS baselines across differing line ending formats (`\r\n` vs `\n`).
- Implement workspace boundary confinement and inspection operations (`read_file`, `get_file_hash`, `search_code`) in `core/engine.py`.
- Register `read_file`, `get_file_hash`, and `search_code` as FastMCP tools on `server.py` conforming to JSON schemas in `protocol/schemas/`.
- Introduce specific standardized CEMP error exceptions in `errors/` for `E_INVALID_RANGE` (-32003), `E_PATH_TRAVERSAL` (-32050), and `E_FILE_NOT_FOUND` (-32051).
- Add unit and conformance test suites verifying schema compliance and edge cases (boundary traversal, out-of-bounds line ranges, regex and literal search context).

## Capabilities

### New Capabilities
- `file-inspection`: Provides SHA-256 CAS hashing, 1-indexed file reading with range extraction, optimistic hash retrieval, context-rich regex and literal code search, and strict workspace boundary protection.

### Modified Capabilities
<!-- None: server-runtime requirements remain unchanged. -->

## Impact

- **Affected Code**: `implementations/python/core/hasher.py`, `implementations/python/core/engine.py`, `implementations/python/server.py`, `implementations/python/errors/system_errors.py`, `implementations/python/errors/__init__.py`.
- **APIs**: Exposes `read_file`, `get_file_hash`, and `search_code` over the CEMP MCP server interface.
- **Dependencies**: Uses Python 3.11+ standard library (`pathlib`, `hashlib`, `re`, `fnmatch`) without external binary dependencies like ripgrep.
- **Verification**: Validated against `protocol/schemas/read_file.json`, `protocol/schemas/search_code.json`, and `protocol/error-codes.md`.
