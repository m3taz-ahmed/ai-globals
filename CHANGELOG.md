# Changelog

## [Unreleased]

### Added
- Externalized persona definitions in `runtime/personas.yaml` loaded by `runtime/persona.py`.
- New Dashboard and MCP security tests.

### Changed
- Hardened `dashboard/server.py` with configurable CORS origin, CSRF header checks, max body size, robust Bearer auth, and `X-Forwarded-For` trust validation.
- Hardened `aios_mcp/aios_server.py` with stricter safe-name validation, path-resolution checks, and input bounds on search/memory tools.
- Updated `graphifyy` pin to `>=0.9.16,<0.9.17` to match CI.
- Renamed `workflows/09-memory-sync.md` to `workflows/17-memory-sync.md` and updated all references/adapters.
- Reduced overlap between maintenance workflow files.
- `runtime/policy.py` now warns on malformed/syntactically invalid conditions.

### Security
- Dashboard CORS, token auth, CSRF, request-size, and origin-trust fixes.
- MCP path-traversal and input-validation fixes.

## [4.22.0]

### Added
- New test discipline rule `[TEST-07]`: full `php artisan test` is extreme-necessity-only; when unavoidable, use the fastest targeted form (`--filter`, `--testsuite`, direct Pest/PHPUnit, `--parallel --stop-on-failure`) or skip tests.
- `[graphify]` optional dependency (`graphifyy>=0.8.20,<0.8.21`) and updated `Dockerfile`, `install.sh`, `install.ps1` to build `integrity.manifest` and `graphify-out/` after all source files are present.
- Budget `period` enforcement: `session`/`hourly`/`daily`/`weekly`/`monthly` with per-process session isolation and atomic `BudgetManager`/`AuditLogger` locks.
- Policy engine validates rule schema, loads all `runtime/policies/*.yaml` files, and skips malformed rules instead of crashing.
- Hybrid context retrieval: `VectorMemory.search` allowlist filtering, `MemoryStore.search_vector(kind/source)`, `ai-os query`, MCP `query_context`, `ingest_memory`, and `search_memory_vector(kind)`.
- Memory ingestion now covers `skills/` (recursive) and `AGENTS.md`, validates AI file structure, and batches source deletions with relation cleanup.
- CLI `ai-os query` for combined FTS + vector search.
- AGENTS.md canonical cross-tool instruction.
- Tool-specific adapters: `.cursor/rules/`, `.claude/`, `.clinerules/`, `.windsurfrules`, `.aider.conf.yml`, `.github/copilot-instructions.md`.
- Runtime kernel: policy, budget, workflow runner.
- Memory service: temporal SQLite-backed memory store with FTS5 and optional vector index.
- Audit logging (`state/audit.log`) for policy, budget, and workflow events.
- MCP server built on FastMCP exposing rules, workflows, memory, policy, and vector search.
- CLI `ai-os` with `--root`, `AGENT_OS_ROOT`, `check --args`, `memory vector`, and `run --context`.
- Dashboard with auto-refresh, CORS, optional bearer auth, and audit endpoint.
- `pyproject.toml`, `ruff`, `mypy`, `pytest` suite, `Dockerfile`, `docker-compose.yml`, and CI workflow.
- Root discovery via `config.py` using `AGENT_OS_ROOT` or install directory.
- Safe AST-based policy evaluator (no `eval`).

### Changed
- Removed all hardcoded `D:/server/.ai` paths.
- `WorkflowRunner` now uses durable SQLite state and `list_workflows` naming.
- `MemoryStore` uses `row_factory`, FTS5, and `rowid`-based relations.

### Changed
- `pyproject.toml` dependency pins now include upper major-version bounds.
- `mypy` exclude regexes now correctly ignore `tests/`, `skills/`, and `scripts/`.

### Removed
- Dead `scripts/ai_memory_engine.py` and `scripts/requirements-memory.txt` (superseded by `memory/vector.py`).

### Security
- Policy `condition` no longer uses `eval`.
- `LIKE` wildcards escaped in memory search.
- Dashboard supports `AGENT_OS_DASHBOARD_TOKEN` bearer auth.
- `ai-os` CLI `check` accepts JSON args only, no shell execution.
