## Purpose

Provides multi-file atomic transactions allowing callers to stage, verify, and commit complex refactorings across multiple files with all-or-nothing consistency and automated rollback guarantees.

## ADDED Requirements

### Requirement: Transaction Initiation via begin_transaction
The system SHALL provide a `begin_transaction` tool conforming to `protocol/schemas/transaction.json` that initializes an isolated multi-file staging context, generates a unique `tx_id`, and configures an expiration TTL. The system SHALL enforce a single active transaction per session and reject attempts to open nested or concurrent transactions.

#### Scenario: Successful transaction start
- **WHEN** `begin_transaction` is invoked while no transaction is currently open
- **THEN** it returns status `open`, a generated `tx_id`, and an expiration time conforming to the transaction schema

#### Scenario: Nested transaction rejection
- **WHEN** `begin_transaction` is invoked while an existing transaction is already active
- **THEN** it rejects the request with error code `-32031` (`E_TRANSACTION_ACTIVE`) and `recoverable: true`

### Requirement: Coordinated Transaction Commit via commit_transaction
The system SHALL provide a `commit_transaction` tool that atomically applies all staged patches associated with `tx_id`. Prior to writing changes, the system SHALL verify that none of the target files on disk have modified since their respective patches were proposed (CAS hash verification). On hash match, the system SHALL capture pre-edit undo snapshots and atomically commit all file updates. If `verify_syntax` is enabled, the system SHALL run syntax checks across all modified files; if any file fails syntax check, the system SHALL automatically rollback all modified files in the batch to their pre-commit state.

#### Scenario: Successful multi-file batch commit
- **WHEN** `commit_transaction` is invoked with a valid `tx_id` containing multiple staged patches where all files match baseline CAS hashes and pass syntax verification
- **THEN** all staged changes are written atomically to disk, returning status `committed`, `tx_id`, and a list of `files_updated`

#### Scenario: Pre-commit collision detection during transaction commit
- **WHEN** `commit_transaction` is invoked but one or more target files on disk were modified after patch staging
- **THEN** no files are updated on disk and the tool rejects with error code `-32011` (`E_FILE_MODIFIED`)

#### Scenario: Automatic rollback on transaction verification failure
- **WHEN** `commit_transaction` applies staged changes to disk but post-write syntax verification fails on any modified file
- **THEN** all modified files in the batch are automatically restored to their pre-commit snapshot and the tool rejects with error code `-32042` (`E_ROLLBACK_TRIGGERED`)

#### Scenario: Commit with non-existent transaction
- **WHEN** `commit_transaction` is invoked with an unknown or expired `tx_id`
- **THEN** it rejects with error code `-32030` (`E_TRANSACTION_NOT_FOUND`)

### Requirement: Transaction Rollback and Cleanup via rollback_transaction
The system SHALL provide a `rollback_transaction` tool that aborts an active transaction, discards all staged patches, prunes temporary staging directories, and releases transaction locks without modifying target files on disk.

#### Scenario: Successful explicit transaction rollback
- **WHEN** `rollback_transaction` is invoked with an active `tx_id`
- **THEN** all staged patches and temporary directories for `tx_id` are purged, the target working tree is untouched, and it returns status `rolled_back` with `discarded_patches_count`

#### Scenario: Rollback with non-existent transaction
- **WHEN** `rollback_transaction` is invoked with an unknown or expired `tx_id`
- **THEN** it rejects with error code `-32030` (`E_TRANSACTION_NOT_FOUND`)

### Requirement: Transaction Concurrency and Conflict Prevention
The system SHALL prevent conflicting concurrent file modifications across transactions. If an active transaction has staged changes for a file, any concurrent transaction or operation attempting to stage edits for the same file SHALL be rejected.

#### Scenario: Concurrent file conflict rejection
- **WHEN** an operation attempts to stage changes to a file that is already locked by another active transaction
- **THEN** it rejects with error code `-32032` (`E_TRANSACTION_CONFLICT`) and `recoverable: true`
