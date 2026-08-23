---
name: aizee
description: Sovereign AI engineering control plane. IDE global bootloader — sets the OS root once and loads all rules, skills, workflows, and tech-stack from it.
license: MIT
---

# aiZee — Global Bootloader

- **Root:** discovered via `AIZEE_ROOT` env or `config.discover_root()` (no hardcoded path).
- Set `AIZEE_ROOT` if not already set. Use `PYTHONIOENCODING=utf-8` on Windows.
- This file is the canonical root pointer. All other OS files discover the root via `AIZEE_ROOT` or `config.discover_root()` and are loaded relative to it.

## Working Directory [DIR-01]
- **Working directory: D:\server\.ai ONLY.** All edits, new files, and modifications go here.
- **D:\server\aizee is READ-ONLY.** Never edit files in izee directly. It is the deployment/usage folder, updated only via the batch update script. If you need to sync changes from .ai to izee, use the batch script.
- When the IDE opens files from izee, copy them to .ai first, edit in .ai, then sync back via the batch script.

## Cold Start
1. Read `global-roles.md`, `global-workflow.md`, and `Memory.md`.
2. Detect personas with `aizee persona detect --multi` and load the returned `skills/` before acting.
3. If the current project has `spec.md`, read it before any action.

## Runtime Gate
- Route every action through `runtime/kernel.py`.
- Use `aizee check <action> --args '{"tokens":N}'` or `Kernel.act` to validate policy + budget.
- No destructive action without explicit user approval.

## Context & Memory
- Detect stack from `package.json` / `composer.json` and load matching `tech-stack/<pkg>-<ver>.md` only after reading the lockfile for the exact version (`[VER-01]`).
- If `graphify-out/graph.json` exists, use `graphify query` or `query_graph` (MCP); never raw grep.
- Query Context7 MCP for external libraries/frameworks before implementation; use `aizee_mcp/aizee_server.py` for global context.
- Run `aizee memory ingest` when `rules/`, `tech-stack/`, or `workflows/` change; update `Memory.md` via `workflows/17-memory-sync.md` after every milestone.

## Quality Gate
Before declaring done, run from the OS root:
- `ruff check .`
- `mypy`
- `aizee test --full` (full suite with coverage, ~35s)
- `python eval/harness.py`
For quick iteration during development: `aizee test` (fast tier, ~12s, no coverage, skips slow/mcp/dashboard/vector).
No `eval` in policy code.

## Project Testing Protocol (ANY project under aiZee)
Every project — Laravel, React, Python, Go, Node — follows two-tier testing `[TEST-07]`:
- **FAST tier** (during iteration): run ONLY targeted tests for the code you touched. ~5s max. See `workflows/testing-tiers.md` for per-stack commands.
- **FULL tier** (before declaring done): run the project's complete test suite + coverage. Must pass green.
- Never run the full suite on every change. Never skip the full suite before done.
- If the project has no test framework, write the first test for the touched code before declaring done `[TEST-09]`.

## Non-negotiable user policy
- No full test suites during iteration — use FAST tier (targeted `--filter=...` / `<file>` only).
- FULL test suite is mandatory before declaring done — no exceptions.
- No `git add .` / `git add -A` (`[GIT-06]`). No `git commit`, `git push`, destructive git, or unauthorized server actions without explicit user approval.
- Delete temporary/scratch/test files immediately after use.

## Shell Compatibility `[SHELL-01]`
- Detect the active shell before running commands. On Windows the default shell is **PowerShell** — never use bash syntax (`&&`, `||`, `2>nul`, `ls`, `cat`, `grep`).
- PowerShell equivalents: `;` instead of `&&`, `if ($?) { ... }` instead of `||`, `Test-Path` instead of `ls ... 2>nul`, `Get-ChildItem` instead of `ls`, `Get-Content` instead of `cat`, `Select-String` instead of `grep`.
- In workflow CMD steps, use `pwsh:` or `ps:` prefix for PowerShell commands on Windows; `bash:` for POSIX shells on Linux/macOS.
- When using `subprocess` in Python, pass command lists (not shell strings) to stay cross-platform. Use `shell=True` only when absolutely necessary and never with user input.

---

## Architecture

aiZee follows a layered design:

- **CLI / Entry Point** — `aizee_cli.py` parses commands, delegates to kernel.
- **Kernel (Facade)** — `runtime/kernel.py` routes to managers.
- **Managers** — `runtime/managers/` (PolicyManager, WorkflowManager, AgentManager, ChatManager).
- **Runtime Modules** — 105 governance modules in `runtime/`.
- **MCP Server** — `aizee_mcp/` exposes 35 tools via FastMCP.
- **Memory** — `memory/` SQLite + FTS5 + vector store.
- **Skills / Workflows / Tech-Stack** — declarative `.md` files loaded at runtime.

### Core Infrastructure

| Module | Purpose |
|--------|---------|
| `runtime/kernel.py` | Facade delegating to managers |
| `runtime/policy.py` | Policy evaluation engine |
| `runtime/budget.py` | Token/cost/call budget tracking |
| `runtime/audit.py` | Append-only audit log |
| `runtime/guardian.py` | Pre-action guardian gate |
| `runtime/probity.py` | Integrity verification |
| `runtime/persona.py` | Auto persona detection |
| `runtime/spec_engine.py` | Spec-driven development (4 phases) |
| `runtime/storage_backend.py` | Pluggable storage abstraction (memory/json/sqlite) |
| `runtime/service_catalog.py` | Multi-index skill/workflow catalog |
| `runtime/schemas.py` | Pydantic schemas + AizeeException hierarchy + PaginatedResult |

### Package Layout

```
aizee/                         # Sovereign root (AIZEE_ROOT)
├── aizee_cli.py               # CLI entry point
├── config.py                  # Root discovery + version
├── runtime/                   # Kernel + 105 governance modules
│   ├── kernel.py              # Facade
│   ├── managers/              # Policy/Workflow/Agent/Chat managers
│   ├── storage_backend.py     # StorageBackend protocol + factory
│   ├── service_catalog.py     # ServiceDescriptor + multi-index catalog
│   ├── schemas.py             # Pydantic + exceptions + pagination
│   └── ...                    # 105 governance modules
├── aizee_mcp/                 # MCP server (35 tools)
├── memory/                    # SQLite + FTS5 + vector
├── skills/                    # 73 persona + lord skills
├── workflows/                 # 36 trigger-based execution protocols
├── rules/                     # Compressed behavioral rules
├── tech-stack/                # 163 version-locked stack references
│   └── spec-driven-templates/ # SDD templates (spec/plan/tasks/constitution/checklist)
└── eval/                      # Agent benchmark harness
```

## First Principles

When making changes, follow these priorities:

1. Preserve policy-governed behavior (never bypass kernel gates)
2. Match existing aiZee patterns (read neighboring code first)
3. Reuse existing modules (don't reinvent storage/catalog/exceptions)
4. Prefer correctness over convenience
5. Keep changes narrow and testable

## Adding a New Runtime Module

1. Create `runtime/<module>.py`
2. Add to `runtime/__init__.py` if it needs exports
3. Wire through `kernel.py` or the relevant manager
4. Add tests in `tests/test_<module>.py`
5. Update `Memory.md` if user-facing
6. Run quality gates: `ruff check .` + `mypy` + `pytest tests/test_<module>.py`

## Adding a New Skill

1. Create `skills/<name>/SKILL.md` (or `skills/<name>.md` for flat)
2. Add frontmatter with triggers, personas, tech_stack
3. Register in `PERSONA_SKILLS` mapping in `runtime/persona.py` if persona-linked
4. Test with `aizee persona detect --multi "<task description>"`
5. Run `aizee memory ingest` to refresh indexes

## Adding a New Workflow

1. Create `workflows/<NN>-<name>.md` (sequential numbering)
2. Add trigger keywords in the header
3. If it uses a runtime engine, document the engine module
4. Update `workflows/README.md` count

## Error Handling

- Raise `AizeeError` subclasses from `runtime/schemas.py`
- Use `PolicyDeniedError` for policy gate failures
- Use `BudgetExceededError` for budget limit hits
- Use `ValidationError` for input validation
- Use `StorageError` for storage backend failures
- All exceptions carry `error_code`, `severity`, and `context` dict
- Never use bare `Exception` — always an `AizeeError` subclass

## Storage Rules

- Use `StorageFactory` from `runtime/storage_backend.py` for new key-value stores
- Do not instantiate `InMemoryStorage` / `JsonFileStorage` / `SqliteStorage` directly
- Existing `MemoryStore` (SQLite) is unchanged — new code opts into the abstraction
- Backends are cached by path — repeat `create()` returns the same instance
- Call `factory.shutdown_all()` on process exit to flush + close

## Common Mistakes

- Bypassing `StorageFactory` and instantiating storage directly
- Using bare `Exception` instead of `AizeeException` subclasses
- Hardcoding paths instead of using `config.discover_root()`
- Assuming framework versions without reading lockfiles (`[VER-01]`)
- Running full test suite during iteration (use FAST tier)
- `git add .` / `git add -A` (`[GIT-06]`)
- Forgetting to update `Memory.md` after milestones
- Writing implementation code without Context7 MCP query first

## Human Handoff

If behavior is unclear:

1. Prefer aiZee spec (`spec.md`) and existing code behavior
2. Then `Memory.md` for historical context
3. Then `global-roles.md` / `global-workflow.md` for governance rules
4. If a task requires broad architectural changes, stop and surface tradeoffs

## Code Style

- Use `from __future__ import annotations` in all Python files
- Strict typing — no `Any` without justification, no `mixed`/`unknown` abuse
- Class <300 lines, method <30 lines (`[CODE-03]`)
- Enums/constants over magic strings (`[CODE-04]`)
- SOLID & DRY (`[CODE-05]`)
- Constructor injection (pass dependencies in `__init__`)
- Self-explanatory code over comments
- Always use braces in conditionals (for JS/TS projects)
- Never leave a `catch`/`except` block empty — log with context
- Follow existing project patterns

## Logging

- Use structured logging (dict-based, not f-strings in hot paths)
- Avoid noisy logs in performance-critical paths
- Log error context: error_code, severity, operation, user (if relevant)

## Pull Request Guidelines

- Keep changes focused — avoid unrelated refactors
- Preserve behavior unless the task explicitly requires change
- Update docs (`Memory.md`, `CHANGELOG.md`) when user-facing
- Conventional commits: `feat:`, `fix:`, `perf:`, `docs:`, `chore:`, `refactor:`
- Stage only files YOU modified (`git add <file>`, never `git add .`)
- No `git commit` / `git push` without explicit user approval
