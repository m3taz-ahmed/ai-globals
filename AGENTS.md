---
name: ai-global-os
description: Sovereign AI engineering control plane. IDE global bootloader — sets the OS root once and loads all rules, skills, workflows, and tech-stack from it.
license: MIT
---

# AI Global OS — Global Bootloader

- **Root:** `D:\server\.ai`
- Set `AGENT_OS_ROOT` to this root if it is not already set. Use `PYTHONIOENCODING=utf-8` on Windows.
- This file is the canonical root pointer. All other OS files discover the root via `AGENT_OS_ROOT` or `config.discover_root()` and are loaded relative to it.

## Cold Start
1. Read `global-roles.md`, `global-workflow.md`, and `state/MEMORY.md`.
2. Detect personas with `ai-os persona detect --multi` and load the returned `skills/` before acting.
3. If the current project has `spec.md`, read it before any action.

## Runtime Gate
- Route every action through `runtime/kernel.py`.
- Use `ai-os check <action> --args '{"tokens":N}'` or `Kernel.act` to validate policy + budget.
- No destructive action without explicit user approval.

## Context & Memory
- Detect stack from `package.json` / `composer.json` and load matching `tech-stack/<pkg>-<ver>.md` only after reading the lockfile for the exact version (`[VER-01]`).
- If `graphify-out/graph.json` exists, use `graphify query` or `query_graph` (MCP); never raw grep.
- Query Context7 MCP for external libraries/frameworks before implementation; use `aios_mcp/aios_server.py` for global context.
- Run `ai-os memory ingest` when `rules/`, `tech-stack/`, or `workflows/` change; update `state/MEMORY.md` via `workflows/17-memory-sync.md` after every milestone.

## Quality Gate
Before declaring done, run from the root:
- `ruff check .`
- `mypy`
- `pytest -q`
- `python eval/harness.py`
No `eval` in policy code.

## Non-negotiable user policy
- No full `php artisan test` suites. Targeted `--filter=...` only, or skip tests.
- No `git add .` / `git add -A` (`[GIT-06]`). No `git commit`, `git push`, destructive git, or unauthorized server actions without explicit user approval.
- Delete temporary/scratch/test files immediately after use.
