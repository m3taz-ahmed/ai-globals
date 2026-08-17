# Changelog

## [Unreleased] — 2026-08-17

### Branding — Renamed to aiZee
- **Project renamed**: AI Global OS → **aiZee** ("The policy layer for AI coding.").
- **Package**: `aios` → `aizee` (pip install aizee).
- **CLI**: `ai-os` → `aizee` (lowercase, no capital Z required).
- **Env vars**: `AGENT_OS_ROOT` → `AIZEE_ROOT`, `AGENT_OS_DASHBOARD_TOKEN` → `AIZEE_DASHBOARD_TOKEN`.
- **MCP server name**: `ai-global-os` → `aizee` in all agent configs.
- **Files renamed**: `aios_cli.py` → `aizee_cli.py`, `aios_mcp/` → `aizee_mcp/`, `aios_server.py` → `aizee_server.py`, `.aios-version` → `.aizee-version`, `aios_mcp_wrapper.py` → `aizee_mcp_wrapper.py`.
- **Clean break**: no backward-compat alias for `ai-os` (per user decision).

### Added — Uninstaller + K8s + Benchmarks
- **Interactive uninstaller** (`runtime/uninstaller.py` + `aizee uninstall`): per-category keep/delete, optional zip backup, preserves learned data (memory/state/brain/.env) by default. 23 tests.
- **GUI uninstaller** (`runtime/uninstaller_gui.py` + `aizee uninstall --gui`): tkinter GUI with Treeview of categories, Keep/Delete toggle, backup path picker, live log output, threaded execution. 7 tests.
- **Update script** (`scripts/update.py` + `update.bat`): git pull from GitHub, compare local vs remote, pull if behind, re-run post-install hooks (pip install, MCP sync, CLI shim, memory ingest). Preserves learned data.
- **Brain backup** (`scripts/backup_brain.py` + `backup.bat`): backs up memory/, state/, brain/, graphify-out/, .env to `aizee-backup-<date>-<time>/` folder. Metadata file included.
- **Brain restore** (`scripts/restore_brain.py` + `restore.bat`): restores from backup folder, overwrites existing data, `--list` flag shows available backups.
- **Smart auto-merge restore** (`restore.bat` / `restore_brain.py --auto`): reads checkpoint from `state/restore_checkpoint.json`, merges all backups newer than last restore. Memory is merged by timestamp (INSERT new, UPDATE if source is newer, SKIP if older). state/brain/.env take the latest backup's version. Checkpoint updated after each merge. Prevents duplicate processing.
- **One-click .bat launchers**: `update.bat`, `backup.bat`, `restore.bat`, `uninstall.bat` — double-click on Windows, no terminal needed.
- **Kubernetes manifests** (`deploy/k8s/`): Deployment, Service, PVCs, Secret, NetworkPolicy, HelmRelease. Production-ready with securityContext, readiness/liveness probes, resource limits.
- **Performance benchmarks** (`runtime/perf_benchmark.py`): Kernel.act, persona.detect, skill.list, memory.search with mean/median/p95/p99 stats. JSON output mode.

### Fixed — P0/P1 from full audit
- **`spec.md` created**: aiZee now dogfoods its own spec-driven workflow.
- **ruff exclusions removed**: `tests/*` and `skills/*` no longer excluded from linting.
- **mypy exclusions removed**: `tests/`, `dashboard/`, `scripts/` no longer excluded from type checking.
- **`--strict-markers` added** to pytest config: unknown markers now error instead of passing silently.
- **`ActionSchema` documented**: `extra="allow"` is intentional for dynamic action params; added docstring + `ge=0` constraints on `tokens`/`cost`.
- **PROPOSAL + FREELANCE personas merged**: 20 → 19 personas. FREELANCE now covers both proposal writing and platform bidding.
- **Dictatorship/Warlord tone softened**: `[DICTATORSHIP]` → `[STANDARDS]`, "God-Tier SRE & Cloud Dictator" → "Principal SRE & Cloud Architect", "SecOps Warlord" → "SecOps Specialist", "Google Play Ecosystem Warlord" → "Google Play Ecosystem Expert".
- **Dashboard auth warning**: prints explicit security warning when no token is set. Env vars renamed to `AIZEE_DASHBOARD_*` with legacy fallback.
- **subprocess audit**: all 30+ subprocess calls confirmed using list args (shell=False default). No shell=True in production code.
- **Memory.md/state conflict resolved**: all rules now point to `Memory.md` at root (not `state/MEMORY.md`). `state/` remains gitignored for runtime data.

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
- Version bumped to 5.0.0 across `pyproject.toml`, `manifest.json`, `config.py`, `.aizee-version`, `README.md`, `README-AR.md`.
- `pyproject.toml`: added `eval*` to setuptools packages.find.
- `aizee_mcp/config.json`: standardized aizee and graphify to use wrapper scripts (consistent with .devin/.claude configs).
- `global-roles.md`: added FREELANCE persona (#20) to match `personas.yaml`.
- 551 new tests added (total: 1121 passing).
- 1222 additional tests added from 45 repo-research enhancements (total: 2343 passing).
- ruff clean across entire codebase.

## [Unreleased]

### Added — 45 new enhancements (repo research driven)

Deep analysis of 22 GitHub repositories yielded 45 enhancements across 3 phases.

#### Phase 1 — High-Impact, Low-Complexity (12 features)
- **Parameterized policy conditions** (`runtime/authorization.py`): YAML-based prefix/suffix/allowlist/denylist/max/min/regex/equals conditions. No code changes for new constraints.
- **Lease generation (fencing token)** (`runtime/authorization.py`): Monotonic fencing token to prevent stale session recovery attacks.
- **3 enforcement modes** (`runtime/authorization.py`): DISABLED (dev), OBSERVE (log but proceed), ENFORCE (full).
- **5-gate evidence-based evaluation** (`eval/harness.py`): Scope → Quality → Evidence → Risk → Communication gates.
- **Single-writer atomic file locking** (`runtime/file_lock.py`): Atomic lock files with fsync + post-write verification. TTL-based expiry.
- **SimHash deduplication** (`memory/simhash.py`): 64-bit SimHash with Hamming distance for near-duplicate detection.
- **Heat-based memory prioritization** (`memory/heat.py`): Multi-factor heat scoring: visits + interaction_length + recency with exponential decay.
- **Stall detection** (`runtime/worktree_pool.py`): Detect stalled agents by hashing output. Auto-respawn with max retries.
- **Tether files** (`runtime/worktree_pool.py`): Persistent assignment files with atomic writes for crash recovery.
- **5-gate file filter** (`runtime/review_engine.py`): Binary → User Include → User Exclude → Default Paths → Extension. Deterministic pre-filtering.
- **Hash-tracked spec manifests** (`runtime/spec_engine.py`): SHA-256 hash tracking of generated spec files. Detects manual edits.
- **Delta-based specs** (`runtime/spec_engine.py`): ADDED/MODIFIED/REMOVED sections. Deltas merge cleanly into main specs.

#### Phase 2 — Medium-Impact, Medium-Complexity (18 features)
- **Execution rings** (`runtime/execution_rings.py`): 4 privilege levels (RING_0_ROOT → RING_3_SANDBOX) with trust-score-based assignment + sudo elevation with TTL.
- **3-stage evaluation gate** (`eval/stages.py`): Mechanical → Semantic → Consensus progressive verification.
- **Saga compensation** (`runtime/saga_compensation.py`): Automatic rollback for multi-step transactions. Best-effort compensation in reverse order.
- **Memory consolidation primitives** (`memory/consolidation.py`): Dry-runnable hygiene jobs: dedupe_entities, summarize_long_traces, detect_superseded_facts.
- **5 cognitive sector classification** (`memory/sectors.py`): Episodic, Semantic, Procedural, Emotional, Reflective. Pattern-based detection + sector-specific decay rates.
- **Temporal knowledge graph** (`memory/temporal.py`): Facts with validity windows (valid_from / valid_to). Point-in-time queries.
- **3-mode delegation** (`runtime/authorization.py`): inherit/narrow/none with hop limits to prevent infinite chains.
- **Runtime state machine** (`runtime/authorization.py`): IDLE → INTENT_SET → PLAN_APPROVED → EXECUTING → TERMINATED. Illegal transitions rejected.
- **Provenance tracking** (`runtime/authorization.py`): USER_TRUSTED, EXTERNAL_UNTRUSTED, SYSTEM_GENERATED. External data cannot grant authority.
- **Three-zone memory compression** (`runtime/memory_compression.py`): Frozen + Compress + Active zones. 60% async, 80% sync compression.
- **CodeGraph builder** (`runtime/codegraph.py`): AST-based code graph with functions and call edges. Mergeable across files.
- **CodeGraph reachability** (`runtime/codegraph.py`): DFS-based path finding from source to sink. Configurable max path length.
- **Budget rate limiting** (`runtime/rate_limiter.py`): Per-agent leaky bucket rate limiting. Configurable burst and sustained rates.
- **Self-healing runtime** (`runtime/self_healing.py`): Heartbeat tracking + crash detection + respawn with max retries.
- **Spec constitution validation** (`runtime/spec_validation.py`): Project governing principles that specs must comply with. Pattern-based validation.
- **Spec test scenarios** (`runtime/spec_validation.py`): Gherkin-style acceptance criteria linked to requirements. Feature file export.
- **Spec linkage graph** (`runtime/spec_validation.py`): Track dependencies between specs, requirements, and code. Impact analysis.
- **Fuzz testing harness** (`runtime/fuzz_testing.py`): Random input generation for PDP robustness testing.

#### Phase 3 — High-Impact, High-Complexity (15 features)
- **Tree-sitter symbol provider** (`runtime/tree_sitter_provider.py`): Language-neutral symbol extraction. Pluggable extractors per language.
- **Diff-based code review** (`runtime/diff_review.py`): Reviews only changed lines (diff-based) instead of full file. Parses unified diff.
- **Budget anomaly detection** (`runtime/budget_anomaly.py`): Z-score statistical anomaly detection. Sliding window baseline.
- **Policy decision caching** (`runtime/policy_cache.py`): TTL-based PDP decision caching. SHA-256 key generation. LRU eviction.
- **Memory decay scheduler** (`memory/decay_scheduler.py`): Periodic decay of memory salience based on sector-specific rates.
- **Semantic code search** (`runtime/semantic_search.py`): TF-IDF-like scoring on code tokens. Finds semantically similar functions.

### Added — Previous unreleased items
- **Global Bootloader documentation** (`docs/BOOTLOADER.md`): full boot sequence diagram and agent integration guide.
- **MCP wrapper script** (`scripts/aizee_mcp_wrapper.py`): replaces inline Python code in MCP config files (security).
- Externalized persona definitions in `runtime/personas.yaml` loaded by `runtime/persona.py`.
- New Dashboard and MCP security tests.
- **At-rest encryption** (`runtime/crypto.py`): Fernet-based encryption for `state/budget.json` when `AIOS_ENCRYPTION_KEY` is set.
- **Schema migration framework** (`runtime/migrations.py`): versioned SQLite schema migrations with backup + retention.
- **Observability module** (`runtime/observability.py`): optional Sentry integration + Prometheus export wrapper.
- **E2E test suite** (`tests/e2e/`): kernel lifecycle, policy evaluation, chat, memory, workflows, metrics.
- **MCP API reference** (`aizee_mcp/API.md`): full documentation of all MCP tools and resources.
- **Feature documentation** (`docs/FEATURES.md`): documents approval_cache, hybrid memory, rule_frontmatter, fresh_context, encryption, migrations, observability, MCP modules, kernel facade.
- **Legal docs**: `NOTICE`, `docs/PRIVACY_POLICY.md`, `docs/TERMS_OF_USE.md`, `docs/AI_DISCLAIMER.md`.
- **Supply-chain CI** (`.github/workflows/supply-chain.yml`): OIDC keyless, SBOM (syft), Cosign, TruffleHog secret scanning, dependency-review.
- **Release workflow** (`.github/workflows/release.yml`): PyPI (OIDC), Docker (GHCR), SBOM, Cosign, GitHub Release.
- **CODEOWNERS** (`.github/CODEOWNERS`) and **branch protection** config (`.github/branch-protection.json`).
- **Docs-guard CI check** in `validate.yml`: verifies `aizee_mcp/API.md`, `LICENSE`, `CODEOWNERS` exist.
- **Async MCP client** (`runtime/mcp_client.py`): `async_call_tool` method using `asyncio.subprocess`.
- **Lazy loading**: `PluginManager` is now a lazy property; `parse_frontmatter` uses `@lru_cache`; `detect_tech_stack` is cached per kernel instance.
- **Migration 4.22.0 → 4.22.1** in `scripts/migrate.py`: runs schema migrations, verifies encryption compatibility, creates new directories.

### Changed
- **Kernel refactored** into facade + managers: `PolicyManager`, `WorkflowManager`, `AgentManager`, `ChatManager` in `runtime/managers/`.
- **MCP server split** into tool modules: `memory_tools.py`, `workflow_tools.py`, `policy_tools.py`, `context_tools.py`, `common.py` in `aizee_mcp/tools/`.
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
- **MCP config externalized**: inline Python one-liners replaced with `scripts/aizee_mcp_wrapper.py`.
- **settings.json deny list expanded**: added `chmod`, `chown`, `sudo`, `dd`, `mkfs`, `nc`, `netcat`, `iptables`, `ufw`, `curl|bash`.
- **install.sh macOS fix**: BSD `sed -i` compatibility with `.bak` suffix.
- Dashboard CORS, token auth, CSRF, request-size, and origin-trust fixes.
- MCP path-traversal and input-validation fixes.
- SQL injection fixed in `memory/store.py`, `hybrid.py`, `graph.py` (whitelisted column/table names).
- Hardcoded `D:/.ai` paths removed from `.devin/mcp_config.json` and `.claude/settings.json`.
- Stub adapters in `aizee_mcp/adapters.py` completed/removed with tracking ticket.
- MIT LICENSE added (2024-2025, Moataz Ahmed).

## [4.22.0]

### Added
- New test discipline rule `[TEST-07]`: full `php artisan test` is extreme-necessity-only; when unavoidable, use the fastest targeted form (`--filter`, `--testsuite`, direct Pest/PHPUnit, `--parallel --stop-on-failure`) or skip tests.
- `[graphify]` optional dependency (`graphifyy>=0.8.20,<0.8.21`) and updated `Dockerfile`, `install.sh`, `install.ps1` to build `integrity.manifest` and `graphify-out/` after all source files are present.
- Budget `period` enforcement: `session`/`hourly`/`daily`/`weekly`/`monthly` with per-process session isolation and atomic `BudgetManager`/`AuditLogger` locks.
- Policy engine validates rule schema, loads all `runtime/policies/*.yaml` files, and skips malformed rules instead of crashing.
- Hybrid context retrieval: `VectorMemory.search` allowlist filtering, `MemoryStore.search_vector(kind/source)`, `aizee query`, MCP `query_context`, `ingest_memory`, and `search_memory_vector(kind)`.
- Memory ingestion now covers `skills/` (recursive) and `AGENTS.md`, validates AI file structure, and batches source deletions with relation cleanup.
- CLI `aizee query` for combined FTS + vector search.
- AGENTS.md canonical cross-tool instruction.
- Tool-specific adapters: `.cursor/rules/`, `.claude/`, `.clinerules/`, `.windsurfrules`, `.aider.conf.yml`, `.github/copilot-instructions.md`.
- Runtime kernel: policy, budget, workflow runner.
- Memory service: temporal SQLite-backed memory store with FTS5 and optional vector index.
- Audit logging (`state/audit.log`) for policy, budget, and workflow events.
- MCP server built on FastMCP exposing rules, workflows, memory, policy, and vector search.
- CLI `aizee` with `--root`, `AIZEE_ROOT`, `check --args`, `memory vector`, and `run --context`.
- Dashboard with auto-refresh, CORS, optional bearer auth, and audit endpoint.
- `pyproject.toml`, `ruff`, `mypy`, `pytest` suite, `Dockerfile`, `docker-compose.yml`, and CI workflow.
- Root discovery via `config.py` using `AIZEE_ROOT` or install directory.
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
- `aizee` CLI `check` accepts JSON args only, no shell execution.
