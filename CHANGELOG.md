# Changelog

## [5.0.0] — 2026-08-13

### Added — 18 new features (competitive analysis driven)
- **Append-only audit log** (`runtime/audit.py`): SHA-256 hash-chained, tamper-evident audit trail with sensitive key redaction.
- **AST validation** (`runtime/ast_validator.py`): plan/diff validation before and after code modifications.
- **Agent benchmark/eval engine** (`eval/agent_benchmark.py`): persona performance benchmarking with multi-metric scoring.
- **OWASP Agentic Top 10 compliance** (`runtime/agentic_security.py` + `runtime/policies/agentic-owasp.yaml`): 10 security controls for agentic systems.
- **MCP security scanning** (`runtime/mcp_security.py`): static analysis scanner for MCP servers and skills (secrets, dangerous imports, eval/exec).
- **Skills marketplace** (`runtime/skills_marketplace.py`): community skill registry with security scanning before install.
- **AI code review engine** (`runtime/review_engine.py`): multi-dimensional review with confidence scoring (security, quality, performance, maintainability).
- **Git-backed memory** (`memory/git_memory.py`): versioned memory store with git branches per persona.
- **Code compression** (`runtime/code_compressor.py`): AST-based compression (~70% token reduction) for Python + regex-based for other languages.
- **OpenTelemetry exporter** (`runtime/otel_exporter.py`): OTLP/JSON trace exporter with fallback file.
- **Parallel agents** (`runtime/worktree_pool.py`): git worktree-based parallel agent execution pool.
- **Spec-driven development** (`runtime/spec_engine.py`): 4-phase workflow (Specify → Plan → Tasks → Implement) with validation gates.
- **Dynamic evolving personas** (`runtime/dynamic_persona.py`): 3-layer evolution (Core/Accumulation/Deep) with experience tracking.
- **Issue tracker integration** (`runtime/issue_tracker.py`): Linear/Jira/Notion unified client.
- **Agent Command Center** (`runtime/command_center.py`): fleet management dashboard with Kanban board.
- **AI slop detection** (`runtime/ai_slop_detector.py`): detects AI-generated code quality issues (stubs, redundant conversions, verbose comments).
- **Voice interface** (`runtime/voice_interface.py`): cross-platform STT/TTS (Windows SAPI, macOS say, Linux espeak/festival).
- **ACP protocol** (`runtime/acp_protocol.py`): Agent Communication Protocol message broker for inter-agent communication.
- **Spec-driven workflow** (`workflows/21-spec-driven.md`): workflow for spec-driven development.

### Changed
- Version bumped to 5.0.0 across `pyproject.toml`, `manifest.json`, `config.py`, `.aios-version`, `README.md`, `README-AR.md`.
- `pyproject.toml`: added `eval*` to setuptools packages.find.
- `aios_mcp/config.json`: standardized ai-global-os and graphify to use wrapper scripts (consistent with .devin/.claude configs).
- `global-roles.md`: added FREELANCE persona (#20) to match `personas.yaml`.
- 551 new tests added (total: 1121 passing).
- ruff clean across entire codebase.

## [Unreleased]

### Added
- **Global Bootloader documentation** (`docs/BOOTLOADER.md`): full boot sequence diagram and agent integration guide.
- **MCP wrapper script** (`scripts/aios_mcp_wrapper.py`): replaces inline Python code in MCP config files (security).
- Externalized persona definitions in `runtime/personas.yaml` loaded by `runtime/persona.py`.
- New Dashboard and MCP security tests.
- **At-rest encryption** (`runtime/crypto.py`): Fernet-based encryption for `state/budget.json` when `AIOS_ENCRYPTION_KEY` is set.
- **Schema migration framework** (`runtime/migrations.py`): versioned SQLite schema migrations with backup + retention.
- **Observability module** (`runtime/observability.py`): optional Sentry integration + Prometheus export wrapper.
- **E2E test suite** (`tests/e2e/`): kernel lifecycle, policy evaluation, chat, memory, workflows, metrics.
- **MCP API reference** (`aios_mcp/API.md`): full documentation of all MCP tools and resources.
- **Feature documentation** (`docs/FEATURES.md`): documents approval_cache, hybrid memory, rule_frontmatter, fresh_context, encryption, migrations, observability, MCP modules, kernel facade.
- **Legal docs**: `NOTICE`, `docs/PRIVACY_POLICY.md`, `docs/TERMS_OF_USE.md`, `docs/AI_DISCLAIMER.md`.
- **Supply-chain CI** (`.github/workflows/supply-chain.yml`): OIDC keyless, SBOM (syft), Cosign, TruffleHog secret scanning, dependency-review.
- **Release workflow** (`.github/workflows/release.yml`): PyPI (OIDC), Docker (GHCR), SBOM, Cosign, GitHub Release.
- **CODEOWNERS** (`.github/CODEOWNERS`) and **branch protection** config (`.github/branch-protection.json`).
- **Docs-guard CI check** in `validate.yml`: verifies `aios_mcp/API.md`, `LICENSE`, `CODEOWNERS` exist.
- **Async MCP client** (`runtime/mcp_client.py`): `async_call_tool` method using `asyncio.subprocess`.
- **Lazy loading**: `PluginManager` is now a lazy property; `parse_frontmatter` uses `@lru_cache`; `detect_tech_stack` is cached per kernel instance.
- **Migration 4.22.0 → 4.22.1** in `scripts/migrate.py`: runs schema migrations, verifies encryption compatibility, creates new directories.

### Changed
- **Kernel refactored** into facade + managers: `PolicyManager`, `WorkflowManager`, `AgentManager`, `ChatManager` in `runtime/managers/`.
- **MCP server split** into tool modules: `memory_tools.py`, `workflow_tools.py`, `policy_tools.py`, `context_tools.py`, `common.py` in `aios_mcp/tools/`.
- **Repository layer** extracted from `workflow.py`, `saga.py`, `memory/store.py` into `runtime/repository.py`.
- **Magic strings replaced** with enums: `Decision`, `StepType`, `CommandType`, `StepStatus`, `RouteName` in `runtime/enums.py`.
- **Dockerfile rewritten**: multi-stage build, digest pinning, `.dockerignore`.
- **Memory leak fixes**: rate_state TTL, metrics eviction, proc_pool cleanup.
- **pytest config**: `--cov-fail-under=80`, markers, plugins (asyncio, xdist, timeout).
- **bandit config** (`.bandit`): excludes tests, skips B101/B608 false positives.
- **Version pinning**: `npx`/`uvx` versions pinned in `install.sh`, `install.ps1`, `.devin/mcp_config.json`, `.claude/settings.json`.
- `install.sh` and `install.ps1` now verify `cryptography` package during install.
- `pyproject.toml` adds `cryptography>=42.0,<46.0` dependency.
- Version bumped to `4.22.1`.

### Security
- **NOTICE license fixed**: Apache 2.0 → MIT to match `LICENSE` and `pyproject.toml`.
- **Dockerfile**: removed fake SHA digests, switched to version tags; removed `--fix` from validate step; production image no longer installs dev dependencies.
- **GitHub Actions**: replaced all fake/placeholder SHAs with version tags (`@v4`, `@v5`, etc.) in `release.yml`, `supply-chain.yml`, `security.yml`.
- **Plugin sandbox hardened**: added `importlib`, `types`, `builtins`, `runpy`, `multiprocessing` to denylist; blocked `__builtins__` subscript bypass.
- **Guardian read-only whitelist**: `_READ_ONLY_ACTIONS` in `PolicyManager` skips guardian gate for read/chat/query actions.
- **run_workflow validation**: added `is_safe_name()` check to prevent path traversal.
- **RemoteA2AAdapter SSL**: added SSL context with `verify_ssl` config + HTTPS endpoint validation.
- **Agent tool whitelist**: `_SAFE_COMMANDS` for server registration + `allowed_tools` whitelist in `call_tool`.
- **MCP config externalized**: inline Python one-liners replaced with `scripts/aios_mcp_wrapper.py`.
- **settings.json deny list expanded**: added `chmod`, `chown`, `sudo`, `dd`, `mkfs`, `nc`, `netcat`, `iptables`, `ufw`, `curl|bash`.
- **install.sh macOS fix**: BSD `sed -i` compatibility with `.bak` suffix.
- Dashboard CORS, token auth, CSRF, request-size, and origin-trust fixes.
- MCP path-traversal and input-validation fixes.
- SQL injection fixed in `memory/store.py`, `hybrid.py`, `graph.py` (whitelisted column/table names).
- Hardcoded `D:/.ai` paths removed from `.devin/mcp_config.json` and `.claude/settings.json`.
- Stub adapters in `aios_mcp/adapters.py` completed/removed with tracking ticket.
- MIT LICENSE added (2024-2025, Moataz Ahmed).

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
