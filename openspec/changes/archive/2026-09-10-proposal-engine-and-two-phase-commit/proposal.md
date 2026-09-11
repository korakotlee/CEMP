## Why

Direct in-place edits (such as blind `sed` streams or raw string replacements) present severe reliability risks for AI-assisted code editing: ambiguous matches silently clobber wrong locations, race conditions overwrite concurrent changes, and interrupted writes corrupt source files. A robust two-phase commit (2PC) workflow with in-memory diff preview, strict occurrence enforcement, Compare-And-Swap (CAS) hash guards, and atomic file replacement eliminates these hazards before touching disk.

## What Changes

- Implement ephemeral in-memory `PatchCache` with UUID `patch_id` generation, state tracking, and 15-minute Time-To-Live (TTL).
- Implement `propose_edit` tool conforming to `protocol/schemas/propose_edit.json`:
  - Enforce `expected_occurrences` (default: 1), rejecting with `E_NO_MATCH` (-32000) or `E_OCCURRENCE_MISMATCH` (-32001).
  - Generate standard unified diff preview and return ephemeral `patch_id`.
- Implement `propose_line_edit` tool conforming to `protocol/schemas/propose_line_edit.json`:
  - Validate 1-indexed start and end line ranges against target file length (`E_INVALID_RANGE`, -32003).
  - Validate `content_hash` against live file SHA-256 digest, rejecting on mismatch with `E_STALE_HASH` (-32010).
  - Generate unified diff preview and return ephemeral `patch_id`.
- Implement atomic file replacement in `core/storage.py` using sibling temporary files, descriptor flushing (`fsync`), and atomic rename (`os.replace`).
- Implement `apply_patch` tool conforming to `protocol/schemas/apply_patch.json`:
  - Re-verify target file content hash prior to disk mutation (`E_FILE_MODIFIED` / `E_STALE_HASH`).
  - Atomically commit replacement content to target file.
  - Mark `patch_id` as applied to prevent duplicate commits (`E_PATCH_ALREADY_APPLIED`, -32022).
- Register `propose_edit`, `propose_line_edit`, and `apply_patch` tools onto FastMCP `server.py`.

## Capabilities

### New Capabilities
- `two-phase-commit`: Implements in-memory patch proposal with dry-run diff previews, CAS hash guards, occurrence enforcement, and APFS atomic commit.

### Modified Capabilities
(None)

## Impact

- Affected Code:
  - `implementations/python/core/engine.py`
  - `implementations/python/core/storage.py`
  - `implementations/python/core/patch_cache.py`
  - `implementations/python/server.py`
  - `implementations/python/tests/`
- Dependencies: Standard library (`difflib`, `uuid`, `os`, `datetime`), `pydantic` v2.
- Protocols/APIs: Implements `propose_edit`, `propose_line_edit`, and `apply_patch` MCP tools aligned with schemas in `protocol/schemas/`.
