# Changelog

## [Unreleased]

### Added
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

### Security
- Policy `condition` no longer uses `eval`.
- `LIKE` wildcards escaped in memory search.
- Dashboard supports `AGENT_OS_DASHBOARD_TOKEN` bearer auth.
- `ai-os` CLI `check` accepts JSON args only, no shell execution.
