# file-inspection Specification

## Purpose
Provides deterministic SHA-256 CAS content hashing, line-indexed file inspection, optimistic hash lookups, context-rich regex and literal code search, and strict workspace boundary protection for CEMP clients.

## Requirements

### Requirement: Deterministic Content Hashing
The system SHALL compute hex-encoded SHA-256 digests over file contents with line endings normalized from CRLF (`\r\n`) to LF (`\n`).

#### Scenario: Line ending normalization consistency
- **WHEN** two files have identical textual content but differing line endings (`\r\n` vs `\n`)
- **THEN** the system produces identical SHA-256 digest strings for both inputs

### Requirement: File Inspection via read_file
The system SHALL provide a `read_file` tool accepting a target `path` and an optional inclusive 1-indexed `line_range` array `[start_line, end_line]`. The tool SHALL return `path`, `lines` as a sequence of `[line_number, line_text]` pairs, `content_hash` matching the full file SHA-256 digest, and `total_lines`.

#### Scenario: Full file inspection with 1-indexed lines
- **WHEN** `read_file` is invoked on an existing file without `line_range`
- **THEN** it returns all lines numbered starting from index 1, the total line count, and the file SHA-256 digest conforming to `protocol/schemas/read_file.json`

#### Scenario: Range-bounded file inspection
- **WHEN** `read_file` is invoked with a valid `line_range` such as `[2, 4]`
- **THEN** it returns only lines 2 through 4 with their correct 1-indexed numbers, while returning the full file `total_lines` and full file `content_hash`

#### Scenario: Out-of-bounds line range rejection
- **WHEN** `read_file` is invoked with inverted line ranges, negative line numbers, or ranges exceeding `total_lines`
- **THEN** it raises a standardized CEMP error with code `-32003` (`E_INVALID_RANGE`) and `recoverable: true`

### Requirement: Optimistic File Hash Retrieval via get_file_hash
The system SHALL provide a `get_file_hash` tool accepting a target `path` that returns `path` and the hex-encoded SHA-256 `content_hash` without transmitting line payloads.

#### Scenario: Rapid hash retrieval for CAS operations
- **WHEN** `get_file_hash` is called on a valid workspace file
- **THEN** it returns the SHA-256 hash matching the digest returned by `read_file`

### Requirement: Context-Rich Code Search via search_code
The system SHALL provide a `search_code` tool supporting literal pattern search and regular expression pattern search across workspace files filtered by `path_glob`, returning match occurrences with configurable surrounding `context_lines`.

#### Scenario: Literal search with context lines
- **WHEN** `search_code` is invoked with a literal string pattern and `context_lines: 2`
- **THEN** it returns matching lines with 1-indexed line numbers, `context_before` array of up to 2 lines, and `context_after` array of up to 2 lines conforming to `protocol/schemas/search_code.json`

#### Scenario: Regex search with glob filtering
- **WHEN** `search_code` is invoked with `regex: true` and a `path_glob` filter
- **THEN** it evaluates the pattern as a regular expression only over files matching the glob filter and reports the total match count

### Requirement: Workspace Boundary Confinement and Security
The system SHALL restrict all inspection operations to designated workspace roots. Any attempt to traverse outside the workspace or inspect protected internal directories SHALL be blocked with standardized CEMP errors.

#### Scenario: Rejection of directory traversal outside workspace
- **WHEN** an inspection tool is invoked with a path containing traversal segments (e.g. `../../etc/passwd`) resolving outside the workspace root
- **THEN** the request is rejected with error code `-32050` (`E_PATH_TRAVERSAL`) and `recoverable: false`

#### Scenario: Non-existent file path handling
- **WHEN** an inspection tool is invoked on a file path that does not exist within the workspace
- **THEN** the request is rejected with error code `-32051` (`E_FILE_NOT_FOUND`) and `recoverable: true`

#### Scenario: Protected file and directory access rejection
- **WHEN** an inspection tool attempts to read inside `.git/` directories or access sensitive files such as `.env`
- **THEN** the request is rejected with error code `-32052` (`E_PERMISSION_DENIED`)
