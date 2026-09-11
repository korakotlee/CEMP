## Context

See `proposal.md` for motivation and background. Ticket 001 established the FastMCP server skeleton (`server.py`), standardized error hierarchy (`errors/`), and in-memory test harness. This design covers the architecture and implementation of the SHA-256 CAS hasher, workspace boundary isolation, and the file inspection engines (`read_file`, `get_file_hash`, `search_code`).

## Goals / Non-Goals

**Goals:**
- Provide deterministic SHA-256 CAS content hashing with normalized line endings (`\r\n` to `\n`).
- Implement 1-indexed, boundary-guarded `read_file` conforming to `protocol/schemas/read_file.json`.
- Implement optimistic `get_file_hash` for fast CAS checks.
- Implement regex and literal `search_code` with surrounding context lines conforming to `protocol/schemas/search_code.json`.
- Enforce strict workspace boundaries and file protection against traversal attacks (`E_PATH_TRAVERSAL`, `E_FILE_NOT_FOUND`, `E_PERMISSION_DENIED`).
- Maintain modular structure under 300 lines per file.

**Non-Goals:**
- Mutation tools (`propose_edit`, `propose_line_edit`, `apply_patch`) - scoped to subsequent tickets.
- External binary search accelerators (e.g. bundling `ripgrep` binaries) - standard library Python is preferred for zero-dependency portability.
- Persistent file caching daemon or background inotify/fswatch indexing.

## Decisions

### Decision 1: Pure Python standard library for inspection and search
- **Context**: Code search could invoke external `ripgrep` or execute via Python's `re` and `pathlib`.
- **Choice**: Implement `search_code` using Python standard library `re`, `fnmatch`, and `pathlib`.
- **Rationale**: Eliminates external binary compilation and path discovery issues across different platforms (macOS, Linux, Windows), keeping the package lightweight and zero-dependency beyond FastMCP.
- **Alternatives Considered**: Subprocess call to `rg`. Rejected due to binary dependency overhead and platform inconsistencies.

### Decision 2: Content hash normalization
- **Context**: Git checkouts on Windows often convert LF to CRLF, which alters raw byte hashes and causes spurious CAS verification failures across operating systems.
- **Choice**: Normalize all `\r\n` line endings to `\n` before computing the SHA-256 digest in `core/hasher.py`.
- **Rationale**: Guarantees identical CAS hashes regardless of checkout platform or newline configuration.

### Decision 3: Path resolution and workspace security guard
- **Context**: Clients can send relative paths (`../../etc/passwd`) or symlinks pointing outside the designated workspace.
- **Choice**: Implement `resolve_workspace_path(path: str, workspace_root: Path) -> Path` that resolves canonical paths using `pathlib.Path.resolve()` and asserts that the resulting path is strictly relative to the workspace root. Raise `PathTraversalError` (`-32050`) if it escapes, and verify target does not touch `.git/` or sensitive files like `.env` (raising `PermissionDeniedError`, `-32052`).
- **Rationale**: Centralized validation guarantees all tools safely inherit workspace boundary protection.

### Decision 4: Modular component separation (<300 lines per file)
- **Context**: Repository rules strictly limit source files to under 300 lines.
- **Choice**: Split the functionality into:
  - `core/hasher.py`: Line ending normalization and SHA-256 CAS computation.
  - `core/workspace.py`: Workspace path resolution, directory traversal checks, and sensitive path filters.
  - `core/engine.py`: Core logic for `read_file`, `get_file_hash`, and `search_code`.
  - `errors/system_errors.py`: Definitions for `PathTraversalError`, `FileNotFoundCempError`, `InvalidRangeError`, and `PermissionDeniedCempError`.
  - `server.py`: Tool exposure and FastMCP wiring.

## Risks / Trade-offs

- **[Risk] High memory consumption on very large repository searches**
  - *Mitigation*: Stream files line by line using generator iteration instead of reading entire files into memory at once; skip binary files and files larger than 10MB by default.
- **[Risk] Path traversal via symbolic links**
  - *Mitigation*: Use `.resolve(strict=False)` to check realpath target against the workspace canonical path.
- **[Risk] Binary file decode errors**
  - *Mitigation*: Open files with `errors="replace"` or catch `UnicodeDecodeError` to gracefully skip non-text files during code search.
