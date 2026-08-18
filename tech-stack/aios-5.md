[TECH] aios-5
[OBJ] aiZee v5.0.0 — sovereign AI engineering control plane. Internal standards for self-reference (dogfooding).
[RULES]
1. [REQ] Root discovery via `config.discover_root()` or `AIZEE_ROOT` env. NEVER hardcode paths (`[OS-ROOT-01]`).
2. [REQ] Route ALL actions through `runtime/kernel.py` → `Kernel.act()` (Policy + Budget + Audit). No direct destructive action (`[OS-RUN-01]`).
3. [REQ] Facade pattern: `Kernel` delegates to `PolicyManager`, `WorkflowManager`, `AgentManager`, `ChatManager`.
4. [REQ] `AizeeException` subclasses from `runtime/schemas.py`: `PolicyDeniedError`, `BudgetExceededError`, `ValidationError`, `StorageError`. Carry `error_code` + `severity` + `context`.
5. [REQ] `StorageFactory` from `runtime/storage_backend.py` for new KV stores. Never instantiate backends directly.
6. [REQ] `ServiceCatalog` from `runtime/service_catalog.py` for skill/workflow indexing. 6-index lookup.
7. [REQ] Two-tier testing (`[TEST-07]`): FAST (targeted, ~5s) during iteration, FULL (complete suite + coverage) before done.
8. [REQ] Quality gate before done: `ruff check .` + `mypy` + `pytest --full` + `python eval/harness.py`.
9. [REQ] `aizee memory ingest` after any `rules/`, `tech-stack/`, or `workflows/` change. Update `Memory.md` via `workflows/17-memory-sync.md`.
10. [REQ] Context7 MCP for external libs before implementation. graphify MCP for codebase exploration.
11. [REQ] Conventional commits: `feat:`, `fix:`, `perf:`, `docs:`, `chore:`, `refactor:` (`[GIT-01]`).
12. [PROHIBIT] `git add .` / `git add -A` (`[GIT-06]`). Stage only files YOU modified.
13. [PROHIBIT] `git commit` / `git push` without explicit user approval.
14. [PROHIBIT] Full test suite during iteration (use FAST tier). Skipping FULL before done.
15. [PROHIBIT] `eval` in policy code. `eval` only in `eval/` harness.
[ARCH]
- CLI: `aizee_cli.py` → Kernel.
- Kernel: `runtime/kernel.py` (facade) → 4 managers in `runtime/managers/`.
- Runtime: 60+ governance modules in `runtime/`.
- MCP: `aizee_mcp/` (27 tools via FastMCP) + `aizee_mcp/tools/` (5 tool modules).
- Memory: `memory/` (SQLite + FTS5 + vector).
- Skills/Workflows/Tech-stack: declarative `.md` loaded at runtime.
[COMPAT]
- v5.0.0: Floci-style storage/catalog, spec-kit SDD templates, Flutter skills.
- Backward-compat: `kernel.policy`/`kernel.guardian`/`kernel.probity` attributes preserved.
