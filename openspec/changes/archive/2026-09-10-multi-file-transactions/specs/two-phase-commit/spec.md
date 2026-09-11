## MODIFIED Requirements

### Requirement: Atomic Patch Application via apply_patch
The system SHALL provide an `apply_patch` tool accepting `patch_id`, optional `tx_id`, and optional `verify_syntax` parameter (default: true). If `tx_id` is provided, the system SHALL validate that `tx_id` corresponds to an active transaction (rejecting with error `-32030` `E_TRANSACTION_NOT_FOUND` if unknown or expired), and stage the patch into the transaction staging area without modifying the target file on disk, returning status `staged`. If `tx_id` is omitted, the system SHALL capture a pre-write undo snapshot and re-verify that the target file content hash matches the proposal baseline. On hash match, it SHALL atomically commit changes to disk using temporary sibling files and atomic file replacement. If `verify_syntax` is enabled, the system SHALL immediately execute automated language syntax verification hooks on the written file. If validation fails, the system SHALL automatically roll back the target file to its pre-write state and return structured diagnostic errors.

#### Scenario: Successful atomic patch application
- **WHEN** `apply_patch` is invoked with a valid pending `patch_id` without `tx_id` and the target file has not been modified since proposal
- **THEN** the target file is atomically updated on disk, the patch status transitions to `applied`, and the tool returns status `applied`, `patch_id`, `path`, and the new SHA-256 `content_hash`

#### Scenario: Successful patch staging into active transaction
- **WHEN** `apply_patch` is invoked with a valid pending `patch_id` and an active `tx_id`
- **THEN** the patch is staged into the transaction staging area without altering the live file on disk, and the tool returns status `staged`, `patch_id`, and `path`

#### Scenario: Patch staging with unknown transaction
- **WHEN** `apply_patch` is invoked with a `tx_id` that is unknown or expired
- **THEN** the request is rejected with error code `-32030` (`E_TRANSACTION_NOT_FOUND`) and `recoverable: true`

#### Scenario: Successful atomic patch application with syntax verification
- **WHEN** `apply_patch` is invoked with a valid pending `patch_id` where `verify_syntax` is true and the modified file has valid syntax
- **THEN** the target file is atomically updated on disk, the patch status transitions to `applied`, and the tool returns status `applied`, `patch_id`, `path`, the new `content_hash`, and a `syntax_check` object indicating verification passed

#### Scenario: Pre-commit collision detection
- **WHEN** `apply_patch` is invoked for a staged patch but the target file on disk was modified after proposal creation
- **THEN** the disk write is aborted, the original file is left untouched, and the tool returns error code `-32011` (`E_FILE_MODIFIED`)

#### Scenario: Automatic rollback on syntax verification failure
- **WHEN** `apply_patch` writes changes to disk but post-write syntax verification fails
- **THEN** the target file is immediately rolled back to its pre-write state using the undo snapshot, and the tool rejects with error code `-32040` (`E_SYNTAX_ERROR`) or `-32042` (`E_ROLLBACK_TRIGGERED`) containing compiler diagnostic messages

#### Scenario: Skip syntax verification when requested
- **WHEN** `apply_patch` is invoked with `verify_syntax: false`
- **THEN** the target file is atomically updated on disk without invoking language syntax checkers, returning status `applied`
