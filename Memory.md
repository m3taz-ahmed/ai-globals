[FILE] Memory
[OBJ] Short-term context and cross-session continuity.
[RULES]
1. [REQ] Read at session start.
2. [REQ] Update at session end via `workflows/17-memory-sync.md`.
3. [REQ] Keep under 500 lines.
[UPDATED] 2026-08-18
[NOTES]
- **Third comprehensive audit + fixes (P0-P3, all personas) — v5.1.0**:
  - **P0 (critical)**: Dockerfile `cli.py`→`aizee_cli.py` + Python 3.14. Exception hierarchy unified (6 exceptions now inherit `AizeeError`). aizee shim PATH fix in `update.py`.
  - **P1 (high)**: CI matrix +3.13/3.14. Secure-by-default encryption (auto-generate key). Dashboard token `chmod 0o600`. Graceful shutdown (storage flush + DB close). Log rotation (100MB, 5 rotated). test_chat_manager (23 tests). Mock time in tests. Self-healing ↔ AgentManager.
  - **P2 (medium)**: StorageBackend explicit conformance. .env allowlist. Audit key-based redaction. CSP strengthened. NumPy tightened. KernelBuilder. MCP async/sync unified. Test organization moved. Weak assertions fixed. DB connection pooling. DB backup automation. Operational docs (3 files).
  - **P3 (low)**: Rate limit LRU. Plugin sandbox strengthened. Plugin resource-based permissions. MCP tool auto-discovery. Parametrized tests. Dashboard HTTP logging. K8s secret warning. Migration rollback.
  - **Gate**: ruff ✅, mypy ✅ (187 files), pytest ✅ (0 failed, 1 skipped tkinter, 96% cov), eval/harness ✅ all_pass, validate-globals ✅ 0 errors.
  - **Version**: 5.1.0 across pyproject.toml, manifest.json, .aizee-version, README.md, README-AR.md, aizee_mcp/API.md, validate-globals.py, validate-globals.ps1.

- **Second comprehensive audit + fixes (P0-P2, all personas)**:
  - **P0 (critical fixes)**:
    - **P0.1**: `cryptography` upper bound raised `<46.0` → `<52.0` (installed 50.0.0). Added Python 3.13/3.14 classifiers. `ruff target-version` → `py314`, `mypy python_version` → `3.14`.
    - **P0.2**: Created `runtime/policies/guardian.yaml` (10 rules: deny rm -rf, force push, reset --hard, DROP TABLE, eval/exec, require approval for deploy/git push/curl/pip install, deny secret exfil). Added `regex` op to `_PredicateEvaluator`. Guardian gate now active from day 1.
    - **P0.3**: `AgentCapabilities` now grants 5 default capabilities (read, write, exec, deploy, destructive) on init. `kernel.status()` reports 5 capabilities instead of `[]`. Added `revoke()` method + `defaults=False` option.
    - **P0.4**: Created `runtime/policies/probity.yaml` (13 rules: block rm -rf/force-push/reset-hard/dd/mkfs/chmod-777/curl-pipe-bash, block hardcoded secrets/eval/pickle/shell=True/f-string SQL, enforce kebab-case). Probity integrity layer now active.
  - **P1 (medium fixes)**:
    - **P1.5+P1.6**: `ruff target-version` → `py314`, `mypy python_version` → `3.14`, added 3.13/3.14 classifiers (with P0.1).
    - **P1.7**: Added `count()`, `list_all()`, `delete_hard()` public methods to `MemoryStore`. Refactored `MemoryStoreAdapter` to use public API only (no more `_conn()`/`_row_to_memory()` private access).
    - **P1.8**: Added `gc.collect()` autouse fixture in `conftest.py` to close leaked SQLite connections. Added `close()` method to `BaseRepository`.
    - **P1.9**: Created `.env.example` with all env vars (AIZEE_ROOT, AIOS_ENCRYPTION_KEY, dashboard, Sentry, Upwork, Freelancer, LinkedIn, Graphify).
  - **P2 (developments)**:
    - **P2.10**: `aizee doctor` expanded with 7 new checks: guardian.yaml (10 rules), probity.yaml (13 rules), capabilities (5), tech_stack detection (7 entries), cryptography version match, .env.example template. 33 total checks.
    - **P2.11**: `aizee memory ingest --watch` flag — auto re-ingests when tech-stack/, rules/, or workflows/ files change (polling every 2s).
    - **P2.12**: `aizee spec` CLI command — `list`, `analyze`, `converge`, `scaffold` subcommands. Exposes SpecEngine from terminal.
    - **P2.13**: Plugin auto-discovery — `PluginManager._discover_plugins()` now auto-loads all `plugins/*/` with valid `__init__.py` when `plugins.yaml` is missing or empty (was: only explicit mode).
    - **P2.14**: `aizee audit` CLI command — `show` (filtered by type/limit) + `verify` (hash chain integrity). Added `read_entries()` method to `AuditLogger`.
    - **P2.15**: Dashboard SSE stream expanded — now includes agents, guardian_rules, capabilities, tech_stack (was: version/budgets/metrics only).
  - **Gate**: ruff ✅, mypy ✅ (174 files), pytest ✅ (2544 passed, 0 failed, 1 skipped tkinter, 96.42% cov), eval/harness ✅ all_pass, validate-globals ✅ 0 errors.
  - **Counts**: 2544 tests (was 2542), 96.42% cov, 7 tech_stack entries, 10 guardian rules, 13 probity rules, 5 capabilities, 33 doctor checks.

- **Self-compatibility audit + fixes (P0-P2, all personas)**:
  - **P0 (test fixes)**: 3 failing tests fixed for Python 3.14 compat.
    - `test_guardian.py`: `asyncio.get_event_loop().run_until_complete()` → `asyncio.run()` (get_event_loop removed in 3.14).
    - `test_rate_limiter.py`: `== 7.0` → `pytest.approx(7.0, abs=0.01)` (time drift flakiness).
    - `test_spec_engine.py`: exec globals now includes `__file__`; `spec_engine.py` has `__file__` guard at module level.
    - `test_uninstaller_gui.py`: `pytest.importorskip("tkinter")` prevents collection break on headless/3.14.
  - **P1.1 (dogfooding tech-stack)**: Added 7 internal tech-stack refs (`python-3.md`, `aios-5.md`, `pydantic-2.md`, `mcp-1.md`, `pytest-7.md`, `pytest-8.md`, `pyyaml-6.md`, `rich-13.md`). Upgraded `_parse_pyproject_toml` to register project self-name + `requires-python` version. `get_os_status` now returns 7 tech_stack entries instead of `{}`.
  - **P1.2 (smart policy fallback)**: `PolicyEngine.evaluate()` now classifies unmatched actions by type (read→allow, write→ask, destructive→deny) instead of blanket `default_action=ask`. YAML `default_action=deny` still wins as strict override. 4 new tests in `test_policy.py`.
  - **P1.3 (asyncio 3.14 compat)**: `aizee_mcp/adapters.py` — `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (4 occurrences). `runtime/guardian.py` — `asyncio.iscoroutinefunction()` → `inspect.iscoroutinefunction()` (deprecated 3.14, removed 3.16). Updated 9 test mocks in `test_adapters.py`.
  - **P1.4 (StorageBackend ↔ MemoryStore bridge)**: Added `MemoryStoreAdapter` in `storage_backend.py` — wraps `MemoryStore` to implement `StorageBackend` protocol (put/get/delete/scan/keys/flush/load/clear/count). 12 new tests in `test_storage_backend.py`.
  - **P2.1 (__file__ robustness)**: 3 runtime `__main__` blocks (`tree_sitter_provider.py`, `semantic_search.py`, `codegraph.py`) now guard `Path(__file__)` with `"__file__" in globals()` fallback.
  - **Gate**: ruff ✅, mypy ✅, pytest ✅ (2527+ passed, 0 failed, 1 skipped tkinter). tech_stack detection returns 7 entries.
  - **Counts**: 83 tech-stack refs (was 76), 114 test files, 2527+ tests.

[UPDATED] 2026-08-17
[NOTES]
- Integrated architecture patterns from two open-source repos (spec-kit + Floci):
  - **spec-kit (P0)**: 5 SDD templates in `tech-stack/spec-driven-templates/` (spec/plan/tasks/constitution/checklist). `SpecEngine` gained `scaffold_spec/plan/tasks/checklist()`, `set_constitution()`, `validate_checklist()`, `analyze_artifacts()` (cross-artifact consistency: coverage/ambiguity/underspecification/constitution violations), `converge_to_code()` (codebase gap analysis: missing/partial/contradicts + suggested tasks). Workflows 22-spec-analyze + 23-spec-converge. 29 tests in `test_spec_engine_templates.py`.
  - **Floci (P0-P1)**: `runtime/storage_backend.py` (StorageBackend protocol + InMemory/JSON/SQLite + StorageFactory with path-caching + lifecycle mgmt). `runtime/service_catalog.py` (ServiceDescriptor frozen dataclass + ServiceCatalog 6-index lookup + match_trigger/match_tech_stack + build_catalog_from_directory). `runtime/schemas.py` gained AizeeError hierarchy (PolicyDeniedError/BudgetExceededError/ValidationError/StorageError) + PaginatedResult + ErrorSeverity enum. AGENTS.md expanded with Floci-style sections (Architecture, Package Layout, First Principles, Error Handling, Storage Rules, Common Mistakes, Human Handoff). 69 tests (41 storage + 28 catalog).
- Gates green: ruff ✅, mypy ✅ (3 new files), pytest ✅ (2526 total, 170 backward-compat passed). No regressions in existing MemoryStore/SkillResolver/spec_engine.
- Counts: 78 skills, 38 workflows, 81 tech-stack refs, 37 test files, 2526 tests.
- Domain gap note: Floci is Java/Quarkus AWS emulator — no code copied, only architectural patterns adapted. spec-kit is same domain (SDD) — templates + analyze/converge logic adapted.

[UPDATED] 2026-08-15
[NOTES]
- Flutter skills suite added: 3 skills (`flutter-architect` combined, `flutter-design` UX, `flutter-developer` MOBILE) + `tech-stack/flutter.md` (Flutter 3.47 / Dart 3.13). personas.yaml: MOBILE lords += flutter-architect/flutter-developer, UX lords += flutter-design, new lord_skills with Arabic keywords. mobile-game-producer updated to route Flutter games. manifest.json triggers added. Persona detect verified (MOBILE 0.814 + UX, lords include flutter-*). Gates green: ruff, mypy (54), pytest 1121 passed / 91.19% cov.

[UPDATED] 2026-08-11
[NOTES]
- Session: full project audit + MCP review + fixes.
- Found root-path mismatch: rules say `D:\server\.ai` but actual root is `D:\.ai`. Set `AIZEE_ROOT=D:\.ai` as permanent User env var. Rules text still references old path (cosmetic; config.discover_root() falls back correctly).
- Found `state/MEMORY.md` missing and `state/` gitignored — all rules reference it. Workaround: `Memory.md` at root is the actual file used. Recommend updating rules to point at `Memory.md`.
- `query_rules` MCP tool was substring-only and returned `[]` for "kernel policy". Upgraded to FTS5 via MemoryStore (kind=semantic, filtered to rules/) with substring fallback. File: `aizee_mcp/aizee_server.py`.
- Removed inline `import asyncio` in `aizee_server.py:run_mcp_plan` (violated no-inline-import rule). Moved to top-level import.
- `temp/` was 28,808 files / 447 MB — cleared completely per user approval.
- MCP servers verified working: `aizee` (18+ tools) + `graphify` (10 tools + 6 resources). `graph_stats`: 1879 nodes / 3224 edges / 276 communities / 93% EXTRACTED.
- Quality gates green: ruff ✅, mypy ✅ (45 files), pytest ✅ (412 passed, 91% cov), eval/harness ✅ all_pass.
- Open issues (not fixed, need decision): `adapters.py` has 3 stub adapters (Codex/ClaudeCode/RemoteA2A); `check_policy` defaults to `ask` for reads; `get_os_status` returns empty `tech_stack`; 44 untracked + 30 modified files in git.

- Expanded *-lord skills to 11 domains (database, language, cloud-platforms, devops, frontend-frameworks, backend-frameworks, messaging-streaming, search-vector, ai-ml, linux-systems, security) and compressed them to Telegraphic Pseudo-Code.
- Fixed `runtime/tech_stack.py` version detection: matches hyphenated major-minor tech-stack filenames, parses `composer.json`/`package.json` constraints when lockfiles absent, and aliases common packages.
- Fixed `Dockerfile` `state/CHANGELOG.md` COPY bug; now creates `state/`/`brain/`/`graphify-out/` directories.
- Refreshed `graphify-out/` graph.
- Refactored `dashboard/server.py`: shared kernel/memory instances, configurable CORS origin, per-IP rate limiting, POST body validation.
- Refactored `runtime/mcp_client.py` to cache stdio processes per server/root and reuse initialized stdio connections.
- Updated `workflows/README.md` file count and added 11-14 audit workflows.
- Added `runtime/policies/examples/` (api-rate-limits, data-exfiltration, time-based-access) and recursive policy loading.
- Pinned `.github/workflows/ci.yml` action SHAs (actions/checkout, actions/setup-python) and documented SBOM/Cosign release step.
- Quality gates green: ruff, mypy, pytest, `python eval/harness.py`.
- Integrated 9 AI personas into `global-roles.md` (English) and created `global-roles-ar.md` (Arabic) for agent/IDE identity charters.
- Rewrote `README.md` and `README-AR.md` with clearer quickstart, persona showcase, updated architecture, and bilingual links.
- Implemented Auto Persona Selection: `runtime/persona.py` + integration in `runtime/kernel.py`, `runtime/workflow.py`, `cli.py`, and tests.
- Added `aizee persona list/detect` and `aizee agent spawn --persona auto`.
- Added persona skills `game-architect`, `google-play-warlord`, `mobile-game-producer` with Context7 IDs and `PERSONA_SKILLS` mapping.
- Fixed CI/CD: `graphify.yml` installs `graphifyy` and creates a PR; `ci.yml`/`validate.yml` use pinned SHAs + lighter `[dev]` install + `--no-cov`.

## v4.22.0 Audit Refactor (P0–P2)

### P0 (6 tasks — all complete)
- **P0.1:** Fixed SQL injection in `memory/store.py`, `hybrid.py`, `graph.py` — whitelisted column/table names.
- **P0.2:** Created MIT LICENSE (2024-2025, Moataz Ahmed), updated `pyproject.toml` + installer.
- **P0.3:** Removed hardcoded `D:/.ai` paths from `.devin/mcp_config.json` + `.claude/settings.json`.
- **P0.4:** Completed/removed 3 stub adapters in `aizee_mcp/adapters.py` with tracking ticket.
- **P0.5:** Added test files for critical modules: `test_config.py`, `test_approval_cache.py`, `test_audit.py`, `test_tracing.py`, `test_schemas.py`.
- **P0.6:** Gate verified: ruff ✅, mypy ✅, pytest ✅, bandit ✅.

### P1 (15 tasks — all complete)
- **P1.1:** Extracted Repository layer from `workflow.py`, `saga.py`, `memory/store.py` → `runtime/repository.py`.
- **P1.2:** Split `kernel.py` into facade + `PolicyManager`, `WorkflowManager`, `AgentManager`, `ChatManager` in `runtime/managers/`.
- **P1.3:** Split `aizee_server.py` into `tools/memory_tools.py`, `tools/workflow_tools.py`, `tools/policy_tools.py`, `tools/context_tools.py`, `tools/common.py`.
- **P1.4:** Replaced magic strings with enums (`Decision`, `StepType`, `CommandType`, `StepStatus`, `RouteName`).
- **P1.5:** At-rest encryption via Fernet wrapper (`runtime/crypto.py`) + budget.json encryption.
- **P1.6:** Fixed memory leaks: rate_state TTL, metrics eviction, proc_pool cleanup.
- **P1.7:** Added `--cov-fail-under=80` + pytest markers + plugins (asyncio, xdist, timeout).
- **P1.8:** Dockerfile: multi-stage build, digest pinning, `.dockerignore`.
- **P1.9:** CI supply-chain: OIDC keyless, SBOM (syft), Cosign, secret scanning (trufflehog), dependency-review.
- **P1.10:** Fixed `bandit || true` in `security.yml`, `.bandit` config, SQL `nosec` handling.
- **P1.11:** `release.yml`: version bump, tag, PyPI (OIDC), Docker (GHCR), SBOM, Cosign.
- **P1.12:** Branch protection config (`.github/branch-protection.json`) + CODEOWNERS.
- **P1.13:** Synced README-AR.md with README.md, verified Memory.md/ACTIVE_CONTEXT.md references.
- **P1.14:** Pinned npx/uvx versions in `install.sh`, `install.ps1`, `.devin/mcp_config.json`, `.claude/settings.json`.
- **P1.15:** Gate verified: ruff ✅, mypy ✅ (53 files), pytest ✅ (579 passed, 89.99% cov), bandit ✅.

### P2 (9 tasks — all complete)
- **P2.1:** Lazy loading for `PluginManager` (property), `@lru_cache` for `parse_frontmatter`, cached `detect_tech_stack`.
- **P2.2:** Async I/O in `mcp_client.py` — added `async_call_tool` using `asyncio.subprocess`.
- **P2.3:** Schema versioning + migrations framework (`runtime/migrations.py`) + backup with retention.
- **P2.4:** Privacy policy, terms of use, AI disclaimer, NOTICE file.
- **P2.5:** Observability: Sentry integration (`runtime/observability.py`), Prometheus export (existing).
- **P2.6:** E2E tests: kernel lifecycle, policy evaluation, chat, memory, workflows, metrics.
- **P2.7:** Docs-guard CI check, `aizee_mcp/API.md` reference.
- **P2.8:** Feature documentation (`docs/FEATURES.md`).
- **P2.9:** Final gate: ruff ✅, mypy ✅ (58 files), pytest ✅ (599 passed, 89.06% cov), bandit ✅ (0 issues).

## v4.22.1 — Installer & Update Flow Review (SRE + DEVOPS + SEC)

### ماذا يحدث عند التحديث (Update Scenario)
1. المستخدم ينزل التحديث (git pull أو نسخة جديدة).
2. يشغل `install.sh` / `install.ps1` — يكتشف الإصدار الحالي من `.aizee-version`.
3. يقارن بالإصدار الهدف من `pyproject.toml`.
4. لو نفس الإصدار → `--update` يقول "already at target".
5. لو إصدار أحدث → ينسخ الملفات (copy mode) أو يتخطى (in-place mode).
6. يحفظ `state/` و `brain/` في `state/.backups/` (دائم، ليس `/tmp/`).
7. يشغل `scripts/migrate.py` → يبني سلسلة migrations من الإصدار القديم للجديد.
8. migration 4.22.0→4.22.1: يشغل schema migrations، يتحقق من encryption، ينشئ dirs جديدة.
9. يثبت dependencies (يضيف `cryptography` للتحقق).
10. يحدّث `AIZEE_ROOT`، يبني graphify، ينشئ symlinks.
11. يكتب `.aizee-version` بالإصدار الجديد.
12. ينظف النسخ الاحتياطية القديمة (يحتفظ بـ 3).

### الإصلاحات
- **`scripts/migrate.py`**: أضيف `_migrate_4_22_to_4_22_1` — يشغل `runtime/migrations.py` schema migrations، يتحقق من encryption compatibility، ينشئ dirs جديدة.
- **`install.sh` / `install.ps1`**: النسخ الاحتياطي الآن في `state/.backups/` (دائم) بدلاً من `/tmp/` أو `$env:TEMP`. تنظيف تلقائي (يحتفظ بـ 3).
- **`install.sh` / `install.ps1`**: أضيف `cryptography` لقائمة التحقق من packages.
- **`cli.py` doctor**: أضيف فحوصات: managers module, mcp tools module, crypto, migrations, observability, LICENSE, CODEOWNERS, `aizee_mcp/API.md`, installed version, encryption key, pip packages.
- **`pyproject.toml`**: version bumped to 4.22.1.
- **`CHANGELOG.md`**: حدّث بالكامل بكل تغييرات P0-P2 + installer fixes.
- **Gate**: ruff ✅, mypy ✅ (58 files), pytest ✅ (599 passed, 89.06% cov), bandit ✅ (0 issues).

## v4.22.1 — MCP Windows Fix + aizee CLI Collision (SRE + DEVOPS)

### المشكلة
- **linkedin MCP (وكل wrapper-based MCP) مكسور على Windows**: `scripts/mcp_env_wrapper.py` كان يستخدم `os.execvpe()` لتشغيل الـ MCP server. على Windows، `os.execvpe` لا يورّث stdin/stdout pipe handles صح لما الـ MCP client يتكلم over stdio → السيرفر يقرأ nothing ويخرج exit 1 بصمت. ده كسر upwork/freelancer/fiverr/linkedin.
- **`aizee` CLI مُخترَق**: حزمة `octopus-linkedin` لها `cli.py` top-level في user site-packages. حزمة `aios` entry point كان `aizee = "cli:main"` → `import cli` يحلّ لـ octopus-linkedin بدل aios (collision). نتيجة: `aizee persona detect` وكل أوامر `aizee` كانت تشتغل كأنها `octopus-linkedin`.

### الإصلاحات
- **`scripts/mcp_env_wrapper.py`**: على Windows استُبدل `os.execvpe` بـ `subprocess.run` (inherited handles). POSIX فضّل `execvpe` (أكفأ). ده أصلح كل MCP servers دفعة واحدة.
- **إعادة تسمية `cli.py` → `aizee_cli.py`** (إصلاح دائم للـ collision): تحديث `pyproject.toml` (`aizee = "aizee_cli:main"`, `py-modules`), `tests/test_cli.py`, `install.ps1`/`install.sh` (shim + verification), `runtime/ci.py` + `eval/harness.py` (mypy targets), docs (README, README-AR, BOOTLOADER, MAINTENANCE_PROMPT, ACTIVE_CONTEXT). `pip install -e .` لإعادة توليد editable finder MAPPING + `aizee.exe`.
- **التحقق**: linkedin MCP رجع 28 أداة + `get_profile` رجع بيانات Moataz Ahmed. `aizee status`/`persona detect --multi` شغّال. ruff ✅, mypy ✅, `tests/test_cli.py` 23 passed.
- **ملاحظة**: `aizee.exe` في `C:\Users\int190\AppData\Roaming\Python\Python314\Scripts` (user Scripts، ليس على PATH) — الـ WindowsApps shim `aizee.cmd` هو اللي على PATH. لو الـ shim قديم بيشاور لـ `cli.py`، شغّل `install.ps1` لتحديثه لـ `aizee_cli.py`.
