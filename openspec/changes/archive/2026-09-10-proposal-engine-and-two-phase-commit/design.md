## Context

See `proposal.md` for motivation. CEMP requires editing operations to be performed in two phases: dry-run staging with unified diff generation, followed by explicit commit. Files must remain strictly bounded within the workspace root, and Python files must stay under 300 lines.

## Goals / Non-Goals

**Goals:**
- Provide in-memory staging via `PatchCache` with UUID `patch_id` and 15-minute TTL.
- Provide `propose_edit` with strict occurrence checking and diff preview.
- Provide `propose_line_edit` with 1-indexed range validation and CAS hash verification.
- Provide APFS-safe atomic file replacement (`core/storage.py`) ensuring zero file corruption under interruption.
- Provide `apply_patch` with CAS re-validation before committing to disk.
- Mount tools on `server.py` conforming to JSON schemas in `protocol/schemas/`.

**Non-Goals:**
- Multi-file transaction management (`tx_id`, covered in Ticket 004).
- Syntax validation hooks and automatic rollback (`verify_syntax`, covered in Ticket 005).
- Git-backed undo tracking (covered in Ticket 006).

## Decisions

### Decision 1: Modular Architecture under 300 Lines
Separate patch management into three focused modules:
- `core/patch_cache.py`: Manages ephemeral proposal records, status transitions (`pending`, `applied`, `expired`), and TTL eviction.
- `core/engine.py`: Performs proposal validation, string/line replacement, and `difflib` unified diff generation without disk mutation.
- `core/storage.py`: Handles atomic disk writes using temporary sibling files and `os.replace`.
*Rationale:* Adheres to single responsibility and keeps each file well below the 300-line repository ceiling.

### Decision 2: Diff Generation via Standard Library `difflib`
Use Python standard library `difflib.unified_diff` with simulated headers `a/<path>` and `b/<path>`.
*Rationale:* Avoids external CLI dependencies (`diff`) or complex external libraries while producing portable, standard unified diffs.

### Decision 3: APFS-Safe Atomic Replacement Pattern
Write content to sibling file `<path>.<uuid>.cemp.tmp`, flush buffers, execute `os.fsync(fd)`, and atomically replace via `os.replace(tmp_path, target_path)`. Any failure cleans up the sibling file in a `finally` block.
*Rationale:* Guarantees atomic replacement on APFS/ext4 filesystems and guarantees the original file remains intact if write or rename is interrupted.

### Decision 4: Optimistic Concurrency Control (CAS)
Validate `content_hash` at both proposal time (for `propose_line_edit`) and commit time (in `apply_patch`).
*Rationale:* Detects concurrent edits or drift immediately, returning `E_STALE_HASH` (-32010) or `E_FILE_MODIFIED` (-32011) to prompt safe re-inspection.

## Risks / Trade-offs

- [Risk: Memory leaks from abandoned patch proposals] -> Mitigation: In-memory `PatchCache` automatically treats items older than 900 seconds as expired (`E_PATCH_EXPIRED`) and purges stale items during lookups.
- [Risk: Concurrent file edits between proposal and apply] -> Mitigation: `apply_patch` re-computes the target file's current SHA-256 digest and compares against proposal baseline before writing.
- [Risk: Dangling temporary files on abrupt process kill] -> Mitigation: Use sibling `.cemp.tmp` naming convention that can be safely cleaned up on startup or garbage collected.
