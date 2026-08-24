[TECH] aizee-5
[OBJ] aiZee v5.7.1 — sovereign AI engineering control plane. Internal standards for self-reference (dogfooding).
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
12. [REQ] `runtime/commands.py` for all CLI command dispatch. Commands module routes subcommands to managers — never bypass with direct manager calls from CLI.
13. [REQ] `runtime/scoped_manager.py` for scoped resource access. Use `ScopedManager.acquire(scope)` / `release(scope)` for multi-tenant isolation. Never access resources outside the acquired scope.
14. [REQ] `runtime/hook_lifecycle.py` for pre/post action hooks. Register hooks via `HookLifecycle.register(phase, callback)`. Hooks fire in registration order; failures abort the lifecycle.
15. [REQ] `runtime/layers.py` for layered execution pipelines. Each layer (`ValidationLayer`, `PolicyLayer`, `ExecutionLayer`, `AuditLayer`) implements `process(context)`. Layers are composable and ordered.
16. [REQ] `runtime/contract_emitter.py` for emitting typed contracts between modules. Use `ContractEmitter.emit(contract_type, payload)` for inter-module communication. Contracts are validated against `schemas.py` at emission time.
17. [PROHIBIT] `git add .` / `git add -A` (`[GIT-06]`). Stage only files YOU modified.
18. [PROHIBIT] `git commit` / `git push` without explicit user approval.
19. [PROHIBIT] Full test suite during iteration (use FAST tier). Skipping FULL before done.
20. [PROHIBIT] `eval` in policy code. `eval` only in `eval/` harness.
[ARCH]
- CLI: `aizee_cli.py` → `runtime/commands.py` → Kernel.
- Kernel: `runtime/kernel.py` (facade) → 4 managers in `runtime/managers/`.
- Runtime: 85 governance modules in `runtime/` (commands, scoped_manager, hook_lifecycle, layers, contract_emitter, middleware, checkpoint, schema_contract, local_responder, spec/ package).
- MCP: `aizee_mcp/` (36 tools via FastMCP) + `aizee_mcp/tools/` (5 tool modules).
- Memory: `memory/` (SQLite + FTS5 + vector).
- Skills: 72 persona + lord skills in `skills/`.
- Workflows: 50 trigger-based protocols in `workflows/`.
- Tech-stack: 163 version-locked stack references in `tech-stack/`.
[COMPAT]
- v5.7.1: local_responder, spec/ package (split from spec_engine.py), inject_persona_context, READ_ACTIONS canonical, sync_docs.py, dashboard open-access + CSP hardening, policy evaluator security fix, guardian fail-closed. 85 runtime modules (26 dead-code removed), 36 MCP tools, 72 skills, 50 workflows.
- v5.5.0: commands module, scoped_manager, hook_lifecycle, layers, contract_emitter, middleware, checkpoint, schema_contract. 88 runtime modules, 35 MCP tools, 66 skills, 30 workflows.
- v5.0.0: Floci-style storage/catalog, spec-kit SDD templates, Flutter skills.
- Backward-compat: `kernel.policy`/`kernel.guardian`/`kernel.probity` attributes preserved.
[REFS]
- Internal: `runtime/kernel.py`, `runtime/commands.py`, `runtime/scoped_manager.py`, `runtime/hook_lifecycle.py`, `runtime/layers.py`, `runtime/contract_emitter.py`.
- Internal: `runtime/schemas.py`, `runtime/storage_backend.py`, `runtime/service_catalog.py`.
