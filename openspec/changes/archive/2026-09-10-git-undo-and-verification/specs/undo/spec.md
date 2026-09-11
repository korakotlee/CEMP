## Purpose

Enables zero-pollution patch reversion and pre-edit snapshots using low-level Git object plumbing and fallback storage without altering Git commits, branches, or working tree state.

## ADDED Requirements

### Requirement: Pre-Write Undo Snapshotting
The system SHALL capture the exact pre-edit file state prior to committing any patch to disk. Within a Git repository, the system SHALL store the pre-edit content into the Git object database via `git hash-object -w` with zero commit, index, or reflog pollution. When outside a Git repository, the system SHALL retain the pre-edit bytes in a fallback storage buffer.

#### Scenario: Pre-edit snapshot in a Git repository
- **WHEN** a patch is applied to a file inside a Git repository
- **THEN** a loose blob is created in the Git object store and its object hash is recorded in the applied patch record without modifying `HEAD`, index, or branch references

#### Scenario: Fallback snapshot outside a Git repository
- **WHEN** a patch is applied to a file outside a Git repository or when Git plumbing is unavailable
- **THEN** the pre-edit file bytes are preserved in fallback storage, allowing subsequent restoration without failing the edit operation

### Requirement: Patch Reversion via undo_last Tool
The system SHALL provide an `undo_last` tool accepting an optional `path` parameter. The tool SHALL locate the most recent applicable patch record and restore the file to its snapshot state using atomic replacement.

#### Scenario: Successful reversion by target path
- **WHEN** `undo_last` is invoked with a `path` that has an applied patch in the undo history
- **THEN** the target file is restored to its pre-edit state, the tool returns status `reverted`, `reverted_patch_id`, `reverted_files`, and `current_hash`, and the patch is marked as reverted

#### Scenario: Successful reversion of globally most recent patch
- **WHEN** `undo_last` is invoked without a `path` parameter and at least one applied patch exists in history
- **THEN** the globally most recent applied patch is identified, its modified file is restored, and the tool returns status `reverted`

#### Scenario: Undo requested with empty history
- **WHEN** `undo_last` is invoked but no eligible patch exists in history (or no patches match the given `path`)
- **THEN** the request fails with error code `-32060` (`E_UNDO_UNAVAILABLE`) and `recoverable: false`
