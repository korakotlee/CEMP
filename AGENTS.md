# AGENTS.md

Welcome to **{{project_name}}**. This document defines operational boundaries, architectural constraints, security invariants, and coding standards for all AI agents (assistants, coding bots, CI automation agents) interacting with this codebase.

---

## 1. Repository Overview & Tech Stack

- **Domain**: 
- **Language**: 
- **Platform**: 
- **UI Framework**: 
- **Core Dependencies**:

---

## 2. Modular Target Graph & Boundaries


```mermaid
flowchart TD

```


---

## 3. Agent Permissions & Operational Invariants

### ✅ Allowed Actions
1. **Targeted Code Modifications**: 
2. **Test-Driven Refinement**: 
3. **Spec & Task Management**: Manage OpenSpec artifacts (`openspec/changes/`, `openspec/specs/`) and tickets (`_tickets/`).
4. **Documentation Updates**: Synchronize `README.md`, `docs/`, and `CHANGELOG.md` when code changes impact user workflows or architectural contracts.

### 🚫 Disallowed Actions
1. **Never Violate File Size Limits**: Source code files must **not exceed 300 lines/file** (excluding generated/config files). Always refactor using SOLID principles and modular abstractions instead of compressing whitespace.
2. **Never Log Plaintext Credentials**: Never output API keys, bearer tokens, or secrets to logs or test outputs.
3. **No Em-Dashes**: Do not use the em-dash character (`—`) in markdown, docs, or commit messages. Use plain dashes (`-`), commas, or parentheses.

---

## 4. Security & Privacy Invariants


---

## 5. Development & Verification Commands

Before proposing or committing any change, agents must verify that the build and test suites pass cleanly:

### Run Full Test Suite

### Run Code Linter

### Build Executable Target

### Run Executable Locally

### Capture Application Window Screenshot
Capture a high-resolution, isolated window screenshot for documentation or visual verification:
```bash
swift .agent/skills/capture-app-screenshot/scripts/capture_window.swift docs/images/app-screenshot.png
```

---

## 6. Coding & Engineering Standards

- **File Length**: Maximum **300 lines per file** for all source files across the codebase. Extract helper components, extensions, or view subcomponents into separate files when approaching this limit.
- **Documentation**:
- **Concurrency**:
- **Logging**:
  Implement central logging and use that
- **Git & Commits**:
  - Follow Conventional Commits format: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`.
  - Keep commits atomic with fewer than 400 diff lines per commit where practical.

---

## 7. Change Management Workflows

- **Tickets**: Track feature work and defects in `_tickets/`. Completed tickets move to `_tickets/done/`.
- **OpenSpec**:
  - Propose new features via `openspec/changes/<change-id>/`.
  - Delta specifications live under `openspec/specs/<capability>/spec.md`.
  - Tasks follow strict TDD ordering (write failing test first, implement feature, refactor).
- **Documentation Sync**: When updating APIs or architecture, update [docs/technical-guide.md](docs/technical-guide.md), [docs/user-guide.md](docs/user-guide.md),  [docs/design.md](docs/design.md), and [README.md](README.md).
