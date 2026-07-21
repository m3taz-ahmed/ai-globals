# Active Context

## 2026-07-21 (9) — Persona Skills + CI/CD Hardening

- Created three new persona skills with Context7 IDs:
  - `skills/game-architect/SKILL.md`
  - `skills/google-play-warlord/SKILL.md`
  - `skills/mobile-game-producer/SKILL.md`
- Added `PERSONA_SKILLS` mapping in `runtime/persona.py`; `detect()` now returns `skill` field.
- Updated `AGENTS.md` and synced all agent config files (`.windsurfrules`, `.cursor/rules/ai-global-os.mdc`, `.claude/CLAUDE.md`) to load the skill returned by persona detection.
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
- Updated `Memory.md` and `state/MEMORY.md`.
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

- Completed AI Global OS v4.21.0 full-refactor milestone: P0 audit fixes, P1 enhancements, and P2 strategic features.
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
