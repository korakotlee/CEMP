# CEMP Error Codes Registry

This document defines the standardized error codes for the Code Editing MCP Protocol (CEMP). Conforming CEMP servers MUST return errors structured according to this registry to enable predictable recovery workflows for AI agents and developer hosts.

---

## 1. Error Payload Structure

When a tool invocation or protocol operation fails, the server MUST return an error object containing at least the following fields:

```json
{
  "code": -32001,
  "name": "E_OCCURRENCE_MISMATCH",
  "message": "String matched 3 times; expected exactly 1.",
  "data": {
    "expected_occurrences": 1,
    "actual_occurrences": 3,
    "matches": [
      {"line": 14, "preview": "def process_data(value):"},
      {"line": 42, "preview": "def process_data(value):"},
      {"line": 89, "preview": "def process_data(value):"}
    ]
  },
  "recoverable": true,
  "suggested_action": "EXPAND_CONTEXT"
}
```

---

## 2. Standard Error Registry

Error codes follow JSON-RPC 2.0 reserved application error ranges (`-32000` to `-32099`).

| Code | Symbolic Constant | Description | Recoverable | Suggested Action |
|---|---|---|---|---|
| `-32000` | `E_NO_MATCH` | `old_str` or line range was not found in target file. | Yes | `RE_INSPECT` (Call `read_file` to verify current content) |
| `-32001` | `E_OCCURRENCE_MISMATCH` | `old_str` matched more or fewer times than `expected_occurrences`. | Yes | `EXPAND_CONTEXT` (Include more surrounding lines in `old_str`) |
| `-32002` | `E_AMBIGUOUS_MATCH` | Target string is ambiguous across the target scope. | Yes | `EXPAND_CONTEXT` or use `propose_line_edit` |
| `-32003` | `E_INVALID_RANGE` | Specified line numbers are negative, inverted, or exceed total lines. | Yes | `RE_INSPECT` (Check `total_lines` from `read_file`) |
| `-32010` | `E_STALE_HASH` | File content hash differs from `content_hash` provided in request (CAS failure). | Yes | `RE_READ_AND_REBASE` (Re-read file, re-apply changes to fresh hash) |
| `-32011` | `E_FILE_MODIFIED` | File was modified on disk while a patch was pending or transaction active. | Yes | `RE_READ_AND_REBASE` |
| `-32020` | `E_PATCH_NOT_FOUND` | `patch_id` does not exist in staging memory. | Yes | `RE_PROPOSE` (Re-run proposal step to obtain valid `patch_id`) |
| `-32021` | `E_PATCH_EXPIRED` | `patch_id` has expired from cache (TTL default: 15 minutes). | Yes | `RE_PROPOSE` |
| `-32022` | `E_PATCH_ALREADY_APPLIED` | `patch_id` was already committed to disk. | No | `NO_ACTION` |
| `-32030` | `E_TRANSACTION_NOT_FOUND` | `tx_id` does not correspond to an open transaction. | Yes | `BEGIN_TRANSACTION` |
| `-32031` | `E_TRANSACTION_ACTIVE` | An open transaction is already active on this session (nested transactions disallowed). | Yes | `COMMIT_OR_ROLLBACK_EXISTING` |
| `-32032` | `E_TRANSACTION_CONFLICT` | Two transactions target overlapping file sets. | Yes | `ABORT_AND_RETRY` |
| `-32040` | `E_SYNTAX_ERROR` | Syntax check failed post-write (`py_compile`, `node --check`). | Yes | `FIX_SYNTAX_AND_RETRY` (Rollback automatically performed) |
| `-32041` | `E_TESTS_FAILED` | Post-commit test hook failed. | Yes | `INSPECT_TEST_OUTPUT` |
| `-32042` | `E_ROLLBACK_TRIGGERED` | Verification failed and the changes were automatically rolled back. | Yes | `INSPECT_ERRORS` |
| `-32050` | `E_PATH_TRAVERSAL` | Requested path attempts traversal outside permissible workspace roots (`../`). | No | `RESTRICT_TO_WORKSPACE` |
| `-32051` | `E_FILE_NOT_FOUND` | File does not exist on filesystem. | Yes | `CHECK_PATH` or `create_file` |
| `-32052` | `E_PERMISSION_DENIED` | Insufficient filesystem read or write permissions. | No | `CHECK_PERMISSIONS` |
| `-32053` | `E_IS_DIRECTORY` | Expected regular file, but path points to a directory. | No | `CHECK_PATH` |
| `-32060` | `E_UNDO_UNAVAILABLE` | No git history or previous patch available to undo. | No | `NO_ACTION` |
| `-32061` | `E_GIT_DIRTY_CONFLICT` | Working tree has unstaged modifications conflicting with undo/reversion. | Yes | `STASH_OR_COMMIT` |

---

## 3. Conformance Requirements

1. Servers MUST use the exact negative integer codes and symbolic constants defined above.
2. Servers MUST include the `recoverable` boolean flag in all error responses.
3. Servers MAY include supplementary metadata in the `data` dictionary (e.g. line numbers of conflicting matches or compiler diagnostic output).
