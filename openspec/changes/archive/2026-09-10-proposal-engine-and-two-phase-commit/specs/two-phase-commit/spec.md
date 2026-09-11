## Purpose

Enables safe, non-destructive code editing through a two-phase commit protocol providing dry-run diff preview, strict occurrence enforcement, Compare-And-Swap (CAS) hash protection, and atomic disk replacement.

## ADDED Requirements

### Requirement: In-Memory Patch Proposal via propose_edit
The system SHALL provide a `propose_edit` tool accepting a target `path`, `old_str`, `new_str`, and optional `expected_occurrences` (default: 1). The tool SHALL validate occurrence counts against target file content in memory without modifying the file on disk, returning an ephemeral `patch_id`, `match_count`, and a standard unified diff preview.

#### Scenario: Successful exact match proposal
- **WHEN** `propose_edit` is invoked on an existing file where `old_str` appears exactly `expected_occurrences` times
- **THEN** it returns status `ok`, an ephemeral `patch_id`, `match_count` matching the occurrences, and a valid unified diff preview conforming to `protocol/schemas/propose_edit.json`

#### Scenario: No match rejection
- **WHEN** `propose_edit` is invoked with an `old_str` that does not occur in the file
- **THEN** it rejects the proposal with standardized CEMP error code `-32000` (`E_NO_MATCH`) and `recoverable: true`

#### Scenario: Occurrence count mismatch rejection
- **WHEN** `propose_edit` is invoked where `old_str` matches a count differing from `expected_occurrences`
- **THEN** it rejects the proposal with error code `-32001` (`E_OCCURRENCE_MISMATCH`), providing actual match count and line locations in the error data payload

### Requirement: Line-Bounded Patch Proposal via propose_line_edit
The system SHALL provide a `propose_line_edit` tool accepting `path`, 1-indexed inclusive `start_line` and `end_line`, replacement `new_content`, and pre-condition `content_hash`. The tool SHALL validate line boundaries and content hashes before staging the patch in memory.

#### Scenario: Successful line-range proposal with CAS validation
- **WHEN** `propose_line_edit` is invoked with valid line bounds and a `content_hash` matching current file SHA-256 digest
- **THEN** it returns status `ok`, an ephemeral `patch_id`, `path`, and a unified diff preview showing the line replacements

#### Scenario: Stale hash rejection on concurrent modification
- **WHEN** `propose_line_edit` is invoked with a `content_hash` that differs from the live file SHA-256 digest
- **THEN** it rejects the proposal with error code `-32010` (`E_STALE_HASH`) and `recoverable: true`

#### Scenario: Out-of-bounds line range rejection
- **WHEN** `propose_line_edit` is invoked with `start_line < 1`, `end_line < start_line`, or `end_line > total_lines`
- **THEN** it rejects the proposal with error code `-32003` (`E_INVALID_RANGE`)

### Requirement: Ephemeral Patch Cache Lifecycle
The system SHALL maintain staged patch proposals in an in-memory cache indexed by UUID `patch_id` with an expiration Time-To-Live (TTL) defaulting to 15 minutes (900 seconds).

#### Scenario: Non-existent patch lookup
- **WHEN** a patch operation is requested for an unknown `patch_id`
- **THEN** the request fails with error code `-32020` (`E_PATCH_NOT_FOUND`)

#### Scenario: Expired patch lookup
- **WHEN** a patch operation is requested for a `patch_id` whose creation time exceeds the 15-minute TTL
- **THEN** the request fails with error code `-32021` (`E_PATCH_EXPIRED`) and `recoverable: true`

#### Scenario: Prevention of duplicate patch commit
- **WHEN** an already applied `patch_id` is submitted again to `apply_patch`
- **THEN** the request is rejected with error code `-32022` (`E_PATCH_ALREADY_APPLIED`) and `recoverable: false`

### Requirement: Atomic Patch Application via apply_patch
The system SHALL provide an `apply_patch` tool accepting `patch_id`. Prior to committing changes, the system SHALL re-verify that the target file content hash still matches the proposal baseline. On verification, it SHALL atomically commit changes to disk using temporary sibling files and atomic file replacement.

#### Scenario: Successful atomic patch application
- **WHEN** `apply_patch` is invoked with a valid pending `patch_id` and the target file has not been modified since proposal
- **THEN** the target file is atomically updated on disk, the patch status transitions to `applied`, and the tool returns status `applied`, `patch_id`, `path`, and the new SHA-256 `content_hash`

#### Scenario: Pre-commit collision detection
- **WHEN** `apply_patch` is invoked for a staged patch but the target file on disk was modified after proposal creation
- **THEN** the disk write is aborted, the original file is left untouched, and the tool returns error code `-32011` (`E_FILE_MODIFIED`)
