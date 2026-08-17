# Active Context

## 2026-08-07 — Added freelance-platforms skill, FREELANCE persona, and MCP config
- Created `skills/freelance-platforms/SKILL.md` covering global (Upwork, Fiverr, Freelancer.com) and Arabic (Mostaql, Khamsat, Nabbesh) marketplaces.
- Added `FREELANCE` persona to `runtime/personas.yaml` with Arabic/English keywords and `freelance-platforms` as a loadable lord skill.
- Configured MCP servers in `.devin/mcp_config.json` (disabled by default): `upwork` (npx @furkankoykiran/upwork-mcp), `freelancer` (npx freelancer-mcp-server), `fiverr` (uvx fiverr-mcp-server). Added `.devin/mcp_config.local.json` template and `.gitignore` entries.
- Created `workflows/20-freelance-pipeline.md` and added `freelance` triggers to `manifest.json`.
- Updated `runtime/tests/test_persona.py` to expect 20 personas (including FREELANCE).
- Quality gates green: `ruff check .`, `mypy .`, `pytest -q` (412 passed), `python eval/harness.py` all_pass true.
- Ran `ai-os memory ingest` and `graphify update .`.

## 2026-08-06 (24) — Integrated all 15 features into runtime, MCP, dashboard
- Completed the integration follow-up:
  - `runtime/kernel.py` now loads and uses `guardian`, `probity`, `metrics`, `tracer`, `preloop`, `governance`, and `sovereign` on every `Kernel.act()`.
  - `aios_mcp/aizee_server.py` exposes new MCP tools: `get_metrics`, `get_os_status`, `lint_python`, `build_schema_graph`, `compile_rule_files`, `run_guardian_check`, `list_capabilities`, `run_mcp_plan`.
  - `dashboard/server.py` exposes new HTTP endpoints: `/api/guardian`, `/api/capabilities`, `/api/tracing`, `/api/lint`.
  - Added `tests/integration/test_new_features.py` covering kernel governance modules, metrics, astryx, sovereign, preloop, and probity.
- Quality gates green: `ruff check .`, `mypy`, `pytest -q` (412 passed), `python eval/harness.py` all_pass true, and `graphify update .`.

## 2026-08-06 (25) — Hardened install.ps1 and verified first/ reinstall in isolated environment
- Rewrote `install.ps1` to be idempotent and re-install safe:
  - Added `-WhatIf`, `-SkipPip`, `-SkipGraphify` switches.
  - Preserves `state/` and `brain/` across installs.
  - Excludes `__pycache__`, `.pyc`, `.pytest_cache`, `node_modules`, `temp`, etc. from copy.
  - Uses `--force-reinstall` on pip to update an existing install.
  - Sets `AGENT_OS_ROOT` as a user environment variable.
  - Backs up and re-creates config symlinks/junctions.
  - Adds CLI self-test at end.
- Tested first install and re-install in an isolated temp environment (separate venv, temp `AGENT_OS_ROOT`/`USERPROFILE`/`LOCALAPPDATA`). Both runs succeeded and `CLI OK` reported.
- Cleaned up the temp test directory.
- Completed the integration follow-up:
  - `runtime/kernel.py` now loads and uses `guardian`, `probity`, `metrics`, `tracer`, `preloop`, `governance`, and `sovereign` on every `Kernel.act()`.
  - `aios_mcp/aizee_server.py` exposes new MCP tools: `get_metrics`, `get_os_status`, `lint_python`, `build_schema_graph`, `compile_rule_files`, `run_guardian_check`, `list_capabilities`, `run_mcp_plan`.
  - `dashboard/server.py` exposes new HTTP endpoints: `/api/guardian`, `/api/capabilities`, `/api/tracing`, `/api/lint`.
  - Added `tests/integration/test_new_features.py` covering kernel governance modules, metrics, astryx, sovereign, preloop, and probity.
- Quality gates green: `ruff check .`, `mypy`, `pytest -q` (412 passed), `python eval/harness.py` all_pass true, and `graphify update .`.

## 2026-08-06 (22) — Repository study executed
- Goal: Execute `.ai/repos-study.md` and produce `.ai/repos-report.md`.
- Cloned 31 of 32 listed repositories into `temp/repos-study/`; `mnemopay/praetor` not found.
- Analyzed repos via parallel subagents by category.
- Report: 15 adopt, 11 watch, 6 skip. Top starts: guardian-angel, awesome-design-md, orchestration-mcp, ai-rules, prometheus-client, synaptic-memory.
- Added Section 9 (Architect's opinion, feature importance map, 90-day integration plan) to the report.
- Temp directory retained per user request.

## 2026-08-06 (21) — Comprehensive project review and all three fix batches
- Adopted ARCH/PRODUCT/QA/SRE/SEC/DEV/PERF/DOC personas for a full review of aiZee v4.22.0.
- Created `.ai/review-findings.md` and `.ai/repos-study.md` (agent meta-prompt + 30+ repos to study).
- Finished third batch: plugin AST sandbox, dashboard token auth, MCP per-key send lock, Pydantic-specific exception handling, budget `_dirty` flag, `[TRIGGER]` tags for all workflows, new `18-data-migration` and `19-incident-response` workflows, rule duplication cleanup, `.github/dependabot.yml`, `CODEOWNERS`, `security.yml`, `runtime/tests/test_security.py`, `scripts/validate-globals.py` workflow count check.
- Updated `rules/vocabulary.md` with `[GIT-06]` and `README.md`/`workflows/README.md`/`README-AR.md` counts to 29.
- Quality gates green: `ruff`, `mypy`, `pytest -q` 361 passed, `python eval/harness.py` all_pass true.
- All changes staged; no commit/push.

## 2026-08-03 (20) — Research, useful-repos, skills, examples, evaluation, DESIGN.md, and dashboard refresh
- Surveyed 50 top GitHub repositories across Programming, UI/UX, Structure Design, Responsive Design, and Databases.
- Updated `tech-stack/useful-repos.md` with 55 verified entries (deduplicated `saadeghi/daisyui`).
- Added Context7 IDs to `skills/database-lord/SKILL.md`, `skills/frontend-ui-expert.md`, `skills/frontend-frameworks-lord/SKILL.md`, `skills/backend-frameworks-lord/SKILL.md`.
- Created `skills/examples/clean-architecture.md`, `skills/examples/responsive-tokens.md`, `skills/examples/database-internals.md`.
- Evaluated `facebook/astryx` and `VoltAgent/awesome-design-md` as MCP-native design systems; added the decision to `tech-stack/design-foundations.md`.
- Created `DESIGN.md` at project root, inspired by Sentry and Linear templates from `awesome-design-md`.
- Refreshed `dashboard/index.html` and `dashboard/index.css` to match `DESIGN.md`: dark-first AI command center, cyan/violet/lime tokens, command palette (`Cmd/Ctrl+K`), status pills, bento metric cards, glass panels.
- Ingested `DESIGN.md` into memory; restarted dashboard server on port 3000.
- Quality gates green: `ruff`, `mypy`, `python eval/harness.py` all_pass true.
- `graphify` and `ai-os memory ingest --root D:\\server\\.ai` run to sync memory and knowledge graph.

## 2026-08-03 (19) — Research top UI/UX/Responsive Design GitHub repos
- Surveyed widely-used, responsive UI/UX design systems on GitHub and updated `tech-stack/useful-repos.md`.
- Added verified, high-impact repositories:
  - `saadeghi/daisyui` — popular open-source Tailwind CSS component library, responsive by default.
  - `shadcn-ui/ui` — copyable, accessible components.
  - `carbon-design-system/carbon` — IBM's accessible enterprise design system.
  - `DouyinFE/semi-design` — design-to-code system with 3000+ tokens.
  - `facebook/astryx` — Meta's open-source, agent-ready design system.
- Quality gates green after `tech-stack` change: `ruff`, `mypy`, `python eval/harness.py` all_pass true.
- `graphify update .` and `ai-os memory ingest` re-run.

## 2026-08-03 (18) — P0.1 Fresh-Context Boundary in runtime/kernel.py
- Added `fresh_context` parameter to `Kernel.act`, `run_workflow`, `chat_message`, and `run_saga`.
- `fresh_context` resets per-session budget counters by generating a new `session_id` passed to `BudgetManager`.
- `fresh_context` deep-copies workflow/saga context and strips/re-derives `persona`/`personas`/`skill`/`skills`/`lords` to avoid carrying over auto-injected keys.
- `fresh_context` in `chat_message` creates a new `ChatSession` with a generated `session_id` and passes it to `act` for a clean chat budget boundary.
- Updated `runtime/budget.py` `check`/`_period_key`/`_reset_if_needed` to accept an explicit `session_id`.
- Added 3 tests in `runtime/tests/test_kernel.py` for budget session reset, fresh chat session, and fresh workflow context.
- Quality gates green: `ruff`, `mypy`, `pytest -q` 352 passed, `python eval/harness.py` all_pass true.
- `graphify update .` and `ai-os memory ingest` run.

## 2026-08-03 (17) — P0.2 Conditional Rules with YAML Frontmatter
- Integrated `runtime/rule_frontmatter.py` into `runtime/skill_resolver.py`:
  added `resolve_with_frontmatter`, `load_with_frontmatter`, and `list_active_skills`.
- Filtered skill lists in `runtime/persona.py` using runtime context (personas, paths, stack);
  added `_is_active_skill` helper to keep missing skill names while filtering by frontmatter when on disk.
- Updated `aios_mcp/aizee_server.py::query_rules` to accept `context` and return only active rules.
- Added 34 tests in `runtime/tests/test_rule_frontmatter.py` covering parsing, glob/persona/stack matching,
  `matches_context` edge cases, and `SkillResolver` frontmatter integration.
- Normalized `matches_context` to accept `None` context and string `paths`/`stack`/`personas` values.
- Quality gates green: `ruff`, `mypy`, `pytest -q` 349 passed, `python eval/harness.py` all_pass true.
- Ran `graphify update .` and `ai-os memory ingest`.
- Staged 5 files for commit; P0.1 Fresh-Context Boundary is next.

## 2026-08-03 (16) — Add CV-writer persona and skill
- Created `skills/cv-writer/SKILL.md` for ATS-optimized, bilingual Arabic/English CVs, cover letters, LinkedIn summaries, and portfolio copy.
- Added `CV` persona to `runtime/personas.yaml` with Arabic/English keywords and `cv-writer` lord skill.
- Updated `global-roles.md`, `AGENTS.md`, `.github/copilot-instructions.md` to include the `CV` persona.
- Added `test_detects_cv` and `test_detects_cv_arabic` to `runtime/tests/test_persona.py`.
- Bumped `tool.mypy.python_version` to `3.12` in `pyproject.toml` to fix mypy parse errors with installed numpy type stubs.
- Quality gates green: `ruff`, `mypy`, `pytest -q` 284 passed, `python eval/harness.py` all_pass true.
- Memory ingested and `graphify update .` run.
- Staged 7 files for commit.

## 2026-08-02 (15) — aiZee usability fixes
- Fixed `runtime/policy.py` `NoneType` warning by defaulting `command` to `""` in `PolicyEngine.can()`.
- Added `ai-os skill` CLI subcommand (`list`, `invoke`, `search`) backed by `SkillResolver`.
- Extended `SkillResolver` to search both OS root `skills/` and project `.ai/skills/`.
- Updated `runtime/kernel.py` to pass `project_root` to `SkillResolver` and include `skills` in `status()`.
- Fixed `memory/vector.py` `allowlist` search to ignore missing ids, resolving 2 `test_cli.py` failures.
- Added `.devin/skills/global-os/SKILL.md` and `.windsurf/skills/global-os/SKILL.md` plus `install.ps1` support so the `global-os` skill is discovered by Devin and Windsurf.
- Quality gates green: `ruff`, `mypy`, `pytest -q` 271 passed, `python eval/harness.py` all_pass true.
- Memory ingested and `graphify update . --force` run.

## 2026-07-29 (14) — Update README.md and README-AR.md
- Updated `README.md` and `README-AR.md` badges, lord skill count (11 → 13), lord skill list, and added `mariadb-lord`, `page-sections-lord`.
- Added "Latest additions" / "أحدث الإضافات" sections documenting `mariadb-lord`, `page-sections-lord`, workflow, and persona wiring.

## 2026-07-29 (13) — Add Page Sections Builder Standard
- Created `skills/page-sections-lord/SKILL.md` from the tourx pattern: `Page` model with JSON `content`, Filament `Builder` blocks, translatable fields, static pages, API image transformation.
- Added `skills/page-sections-lord/templates/page-builder-spec.md` with database, Filament, API, and frontend blueprint.
- Added `workflows/15-page-builder-setup.md` for step-by-step scaffold and updated `manifest.json` triggers `/page-builder`, `page builder`, `landing page`.
- Wired `page-sections-lord` into UX and DEV personas with `landing page`, `page builder`, `page sections` keywords.
- Updated `backend-frameworks-lord` and `frontend-frameworks-lord` to cross-reference `page-sections-lord`.
- Quality gates green, installed, memory ingested (7 memories), graphify updated.

## 2026-07-29 (12) — Extend MariaDB Skill for Filament + Nova
- Extended `skills/mariadb-lord/SKILL.md` with Filament and Laravel Nova integration on MariaDB.
- Added Context7 IDs: Filament `/filamentphp/filament`, Filament tenancy `/tomatophp/filament-tenancy`, Filament Shield `/bezhansalleh/filament-shield`, Laravel Nova `/websites/nova_laravel_v5`.
- Added rules: Filament panel tenant model, `filament-shield` RBAC with `--relationships`, Nova resources/policies, `whenServing` authorization, tenant-aware policies.
- Updated `skills/backend-frameworks-lord/SKILL.md` to include Filament/Nova IDs and multi-tenancy guidance.
- Quality gates green, installed, memory ingested (3 memories), graphify unchanged.

## 2026-07-29 (11) — Extend MariaDB Skill for Laravel + Multi-Tenancy
- Extended `skills/mariadb-lord/SKILL.md` with Laravel integration, MariaDB driver, migrations, and multi-tenancy patterns.
- Added Context7 IDs: Laravel `/laravel/docs`, Spatie multi-tenancy `/spatie/laravel-multitenancy`, Stancl tenancy `/archtechx/tenancy`.
- Added multi-tenancy rules: database-per-tenant vs schema-per-tenant vs table-per-tenant, central `landlord` DB, tenant connection switching, `tenants:migrate`, per-tenant backup/restore.
- Updated `skills/backend-frameworks-lord/SKILL.md` to reference MariaDB and multi-tenancy packages.
- Quality gates green, installed, and memory ingested (3 memories).

## 2026-07-29 (10) — Add MariaDB Lord Skill
- Added `skills/mariadb-lord/SKILL.md` with Context7 IDs for official MariaDB docs, Docker image, Node.js/Python connectors.
- Updated `skills/database-lord/SKILL.md` to include MariaDB in description/IDs and delegate deep questions to `mariadb-lord`.
- Wired `mariadb-lord` into DATA and PERF persona lords and added MariaDB/Galera keywords for auto-detection.
- Quality gates green: ruff, mypy, pytest, eval/harness.
- Graphify graph rebuilt; memory ingest run.

## 2026-07-21 (9) — Persona Skills + CI/CD Hardening

- Created three new persona skills with Context7 IDs:
  - `skills/game-architect/SKILL.md`
  - `skills/google-play-warlord/SKILL.md`
  - `skills/mobile-game-producer/SKILL.md`
- Added `PERSONA_SKILLS` mapping in `runtime/persona.py`; `detect()` now returns `skill` field.
- Updated `AGENTS.md` and synced all agent config files (`.windsurfrules`, `.cursor/rules/aizee.mdc`, `.claude/CLAUDE.md`) to load the skill returned by persona detection.
- Improved CI/CD workflows:
  - `graphify.yml` creates a Pull Request instead of pushing directly, and fails on PRs if graph is stale.
  - `ci.yml` and `validate.yml` disable `pytest-cov` with `PYTEST_ADDOPTS: --no-cov` for faster matrix runs.
- Validation: `ruff`, `mypy`, `pytest --no-cov` 263 passed, `eval/harness.py` all_pass true, `validate-globals` zero errors, `graphify update`, `memory ingest` done.

## 2026-07-21 (8) — CI/CD Fix

- Fixed `.github/workflows/graphify.yml`: it was trying `pip install graphify` (package does not exist). Updated to `pip install graphifyy==0.9.16` (official PyPI package; CLI command stays `graphify`), pinned action SHAs, and fixed `git diff`/`commit`/`push` logic.
- Optimized `.github/workflows/ci.yml` and `validate.yml`: pinned SHAs, removed heavy `[vector]` extra from CI install (vector tests use mocks/tolerant fallbacks), and removed redundant `python eval/harness.py` step since `ai-os ci` already runs it.
- Local gates still green: ruff, mypy, pytest 262 passed.

## 2026-07-21 (7) — Auto Persona Selection

- Implemented `runtime/persona.py` with weighted keyword detection for the 9 personas (ARCH, QA, UX, DEV, SRE, SEC, GAME, PLAY, MOBILE).
- Wired `PersonaDetector` into `runtime/kernel.py`: `detect_persona`, `_auto_persona`, `act`, `run_workflow`, `spawn_agent`, and `status`.
- Wired `PersonaDetector` into `runtime/workflow.py`: auto-detects `persona` from workflow context.
- Added `ai-os persona` CLI command (`list` / `detect`) and changed `ai-os agent spawn --persona` default to `auto`.
- Added `runtime/tests/test_persona.py` with 13 tests.
- Quality gates green: ruff, mypy, pytest 262 passed, `python eval/harness.py` all_pass true, `validate-globals` zero errors, `graphify update` rebuilt graph.

## 2026-07-21 (6) — Global Personas & README Refresh

- Analyzed the 9 persona definitions provided by the user and compressed them into Telegraphic Pseudo-Code.
- Rewrote `global-roles.md` (English) with all nine personas: ARCH, QA, UX, DEV, SRE, SEC, GAME, PLAY, MOBILE.
- Created `global-roles-ar.md` (Arabic) with the full persona charter for Arabic-speaking agents/IDEs.
- Rewrote `README.md` and `README-AR.md` with clearer 60-second activation, persona section, updated architecture tree, and bilingual cross-links.
- Quality gates green: ruff, mypy, pytest 249 passed, `python eval/harness.py` all_pass true, `validate-globals` scanned 171 files with zero errors.
- Next: consider deriving dedicated skills from the new personas (game architect, Google Play warlord, mobile game producer) and wiring persona auto-selection into `runtime/kernel.py` or workflows.

## 2026-07-21 (5) — Gap Analysis & P0-P2 Fixes

- Fixed `runtime/tech_stack.py` to match real `tech-stack/` filename conventions, parse `composer.json`/`package.json` constraints, and alias common packages.
- Fixed `Dockerfile` `COPY state/CHANGELOG.md` bug; image now creates `state/`/`brain/`/`graphify-out/` directories.
- Refreshed `graphify-out/` graph.
- Compressed all 11 `*-lord` skills to Telegraphic Pseudo-Code.
- Refactored `dashboard/server.py`: shared kernel/memory instances, configurable CORS origin, per-IP rate limiting, POST body validation.
- Refactored `runtime/mcp_client.py` to pool/reuse stdio MCP processes per server/root.
- Updated `workflows/README.md` file count and added 11-14 audit workflows.
- Added `runtime/policies/examples/` (api-rate-limits, data-exfiltration, time-based-access) and enabled recursive policy loading.
- Pinned `.github/workflows/ci.yml` action SHAs and documented SBOM/Cosign release step.
- Updated `Memory.md`.
- Quality gates green: ruff, mypy, pytest 249 passed, `python eval/harness.py` all_pass true, `ai-os memory ingest` added 12 memories.

## 2026-07-21 (4) — Database & Language Lord Skills

- Resolved Context7 MCP library IDs for the top databases and programming languages.
- Created `skills/database-lord/SKILL.md`: creator-level mastery skill for PostgreSQL, MySQL, MongoDB, Redis, SQLite, SQL Server, Oracle, ClickHouse with Context7 IDs and first-principles checklist.
- Created `skills/language-lord/SKILL.md`: creator-level mastery skill for Python, JavaScript, TypeScript, Java, C#, C++, Go, Rust, PHP, Ruby with Context7 IDs and spec/source references.
- Identified next candidate domains: Cloud (AWS/Azure/GCP), Kubernetes/Docker/Terraform, Linux/Networking, Frontend frameworks (React/Vue/Angular), Backend frameworks (Laravel/Django/Spring/Express), Messaging/Search (Kafka/Elasticsearch), AI/ML (PyTorch/TensorFlow/OpenAI).
- Ran `ai-os memory ingest` (2 new memories).

## 2026-07-21 (3) — Feature Sprint Complete

- Completed all remaining strategic features in order:
  1. Tech-stack auto-detection from `package-lock.json` / `composer.lock` -> `runtime/tech_stack.py` + `ai-os stack detect/show`.
  2. MCP client integration: `runtime/mcp_client.py` sync stdio caller; workflow `[mcp:server.tool(args)]` execution; `ai-os mcp` CLI.
  3. Persistent chat: `runtime/chat.py` sessions stored in `state/chat_sessions.jsonl`; `ai-os chat` REPL; dashboard `/api/chat`.
  4. Dashboard enhancements: new tabs (Sagas, Chat, Tech Stack, Telemetry, System); dark/light theme toggle; Chart.js telemetry bar chart.
  5. CI pipeline: `runtime/ci.py` + `ai-os ci` + updated `.github/workflows/ci.yml`.
  6. Plugin sandboxing: `PluginGuard` with denied/allowed action lists, tool wrappers read from `plugins.yaml` permissions.
  7. Sub-agent orchestrator: `runtime/orchestrator.py` `AgentPool` spawning isolated `Kernel` instances; `ai-os agent spawn/delegate/list/sync`.
- Final validation: ruff + mypy clean, pytest 246 passed, eval/harness.py all_pass true.

## 2026-07-21 (2)

- Completed aiZee v4.21.0 full-refactor milestone: P0 audit fixes, P1 enhancements, and P2 strategic features.
- Key decisions: removed hardcoded `D:/server/.ai` paths via env-aware installs; dashboard now per-request instances with full CORS; MCP server no longer caches `Kernel`/`MemoryStore` and supports `reset_state`; `validate-globals` prunes stale integrity manifest entries; added Pydantic policy/budget schemas; separated `AGENT_PROJECT_ROOT` from `AGENT_OS_ROOT`.
- Added CLI commands: `policy test`, `budget list/usage/set`, `project init`. Dashboard gained `/api/workflows`, `/api/workflow/run`, `/api/metrics`, `/api/health`, and a Workflows tab.
- Workflow engine now dry-runs `[CMD]` steps through policy for `bash:` and `mcp:` directives.
- Docker hardening: non-root user, healthchecks, resource limits, `.dockerignore`, updated Dockerfile/compose.
- Quality gates green: ruff, mypy, pytest 227 passed, eval/harness.py all_pass true, memory ingested 157 entries.
- Next: continue saga reconciliation, multi-project budget isolation, and telemetry metrics pipeline.

## 2026-07-20

- Completed Gobook customer-facing feature integrations: coupon codes in booking wizard, referral codes on registration/OTP login, add-to-calendar buttons, loyalty/referral summary in dashboard/profile.
- Added backend gift-card support with model, service, migrations, and Filament resource; wired into booking pricing.
- Committed to `hotfix/critical-fixes`.
- Quality gates green: pint 1093 files, npm typecheck/lint/build, route/view cache.
- Next: run full PHPUnit suite once Postgres is available; consider customer-side gift-card input in wizard.

## 2026-07-14

- IAMS cleanup continuation: MySQL final, Redis/queue/cache config, font paths fixed, missing indexes added, env/gitignore/phpunit security fixed, model PHPDoc generated, PHPStan level 5 baseline regenerated (181 errors retained), Pint/test/PHPStan green.
- Next: Replace magic strings with Enums, refactor fat controllers/delegation, continue PHPStan baseline reduction.

## 2026-07-14

- Implemented Plugin Architecture + Graphify integration.
- Plugin engine uses explicit `plugins.yaml` manifest (no auto-discovery).
- Graphify plugin exposes `query_graphify` and `sync_graph_to_memory` MCP tools.
- All gates green: ruff, mypy, pytest (221), eval/harness.py.
- Next: consider plugin dependency/sandboxing and ingest `plugins/` rules into memory if needed.
