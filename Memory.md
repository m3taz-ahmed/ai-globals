[FILE] Memory
[OBJ] Short-term context and cross-session continuity.
[RULES]
1. [REQ] Read at session start.
2. [REQ] Update at session end via `workflows/17-memory-sync.md`.
3. [REQ] Keep under 500 lines.
[UPDATED] 2026-08-15
[NOTES]
- Flutter skills suite added: 3 skills (`flutter-architect` combined, `flutter-design` UX, `flutter-developer` MOBILE) + `tech-stack/flutter.md` (Flutter 3.47 / Dart 3.13). personas.yaml: MOBILE lords += flutter-architect/flutter-developer, UX lords += flutter-design, new lord_skills with Arabic keywords. mobile-game-producer updated to route Flutter games. manifest.json triggers added. Persona detect verified (MOBILE 0.814 + UX, lords include flutter-*). Gates green: ruff, mypy (54), pytest 1121 passed / 91.19% cov.

[UPDATED] 2026-08-11
[NOTES]
- Session: full project audit + MCP review + fixes.
- Found root-path mismatch: rules say `D:\server\.ai` but actual root is `D:\.ai`. Set `AGENT_OS_ROOT=D:\.ai` as permanent User env var. Rules text still references old path (cosmetic; config.discover_root() falls back correctly).
- Found `state/MEMORY.md` missing and `state/` gitignored — all rules reference it. Workaround: `Memory.md` at root is the actual file used. Recommend updating rules to point at `Memory.md`.
- `query_rules` MCP tool was substring-only and returned `[]` for "kernel policy". Upgraded to FTS5 via MemoryStore (kind=semantic, filtered to rules/) with substring fallback. File: `aios_mcp/aios_server.py`.
- Removed inline `import asyncio` in `aios_server.py:run_mcp_plan` (violated no-inline-import rule). Moved to top-level import.
- `temp/` was 28,808 files / 447 MB — cleared completely per user approval.
- MCP servers verified working: `ai-global-os` (18+ tools) + `graphify` (10 tools + 6 resources). `graph_stats`: 1879 nodes / 3224 edges / 276 communities / 93% EXTRACTED.
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
- Added `ai-os persona list/detect` and `ai-os agent spawn --persona auto`.
- Added persona skills `game-architect`, `google-play-warlord`, `mobile-game-producer` with Context7 IDs and `PERSONA_SKILLS` mapping.
- Fixed CI/CD: `graphify.yml` installs `graphifyy` and creates a PR; `ci.yml`/`validate.yml` use pinned SHAs + lighter `[dev]` install + `--no-cov`.

## v4.22.0 Audit Refactor (P0–P2)

### P0 (6 tasks — all complete)
- **P0.1:** Fixed SQL injection in `memory/store.py`, `hybrid.py`, `graph.py` — whitelisted column/table names.
- **P0.2:** Created MIT LICENSE (2024-2025, Moataz Ahmed), updated `pyproject.toml` + installer.
- **P0.3:** Removed hardcoded `D:/.ai` paths from `.devin/mcp_config.json` + `.claude/settings.json`.
- **P0.4:** Completed/removed 3 stub adapters in `aios_mcp/adapters.py` with tracking ticket.
- **P0.5:** Added test files for critical modules: `test_config.py`, `test_approval_cache.py`, `test_audit.py`, `test_tracing.py`, `test_schemas.py`.
- **P0.6:** Gate verified: ruff ✅, mypy ✅, pytest ✅, bandit ✅.

### P1 (15 tasks — all complete)
- **P1.1:** Extracted Repository layer from `workflow.py`, `saga.py`, `memory/store.py` → `runtime/repository.py`.
- **P1.2:** Split `kernel.py` into facade + `PolicyManager`, `WorkflowManager`, `AgentManager`, `ChatManager` in `runtime/managers/`.
- **P1.3:** Split `aios_server.py` into `tools/memory_tools.py`, `tools/workflow_tools.py`, `tools/policy_tools.py`, `tools/context_tools.py`, `tools/common.py`.
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
- **P2.7:** Docs-guard CI check, `aios_mcp/API.md` reference.
- **P2.8:** Feature documentation (`docs/FEATURES.md`).
- **P2.9:** Final gate: ruff ✅, mypy ✅ (58 files), pytest ✅ (599 passed, 89.06% cov), bandit ✅ (0 issues).

## v4.22.1 — Installer & Update Flow Review (SRE + DEVOPS + SEC)

### ماذا يحدث عند التحديث (Update Scenario)
1. المستخدم ينزل التحديث (git pull أو نسخة جديدة).
2. يشغل `install.sh` / `install.ps1` — يكتشف الإصدار الحالي من `.aios-version`.
3. يقارن بالإصدار الهدف من `pyproject.toml`.
4. لو نفس الإصدار → `--update` يقول "already at target".
5. لو إصدار أحدث → ينسخ الملفات (copy mode) أو يتخطى (in-place mode).
6. يحفظ `state/` و `brain/` في `state/.backups/` (دائم، ليس `/tmp/`).
7. يشغل `scripts/migrate.py` → يبني سلسلة migrations من الإصدار القديم للجديد.
8. migration 4.22.0→4.22.1: يشغل schema migrations، يتحقق من encryption، ينشئ dirs جديدة.
9. يثبت dependencies (يضيف `cryptography` للتحقق).
10. يحدّث `AGENT_OS_ROOT`، يبني graphify، ينشئ symlinks.
11. يكتب `.aios-version` بالإصدار الجديد.
12. ينظف النسخ الاحتياطية القديمة (يحتفظ بـ 3).

### الإصلاحات
- **`scripts/migrate.py`**: أضيف `_migrate_4_22_to_4_22_1` — يشغل `runtime/migrations.py` schema migrations، يتحقق من encryption compatibility، ينشئ dirs جديدة.
- **`install.sh` / `install.ps1`**: النسخ الاحتياطي الآن في `state/.backups/` (دائم) بدلاً من `/tmp/` أو `$env:TEMP`. تنظيف تلقائي (يحتفظ بـ 3).
- **`install.sh` / `install.ps1`**: أضيف `cryptography` لقائمة التحقق من packages.
- **`cli.py` doctor**: أضيف فحوصات: managers module, mcp tools module, crypto, migrations, observability, LICENSE, CODEOWNERS, `aios_mcp/API.md`, installed version, encryption key, pip packages.
- **`pyproject.toml`**: version bumped to 4.22.1.
- **`CHANGELOG.md`**: حدّث بالكامل بكل تغييرات P0-P2 + installer fixes.
- **Gate**: ruff ✅, mypy ✅ (58 files), pytest ✅ (599 passed, 89.06% cov), bandit ✅ (0 issues).

## v4.22.1 — MCP Windows Fix + ai-os CLI Collision (SRE + DEVOPS)

### المشكلة
- **linkedin MCP (وكل wrapper-based MCP) مكسور على Windows**: `scripts/mcp_env_wrapper.py` كان يستخدم `os.execvpe()` لتشغيل الـ MCP server. على Windows، `os.execvpe` لا يورّث stdin/stdout pipe handles صح لما الـ MCP client يتكلم over stdio → السيرفر يقرأ nothing ويخرج exit 1 بصمت. ده كسر upwork/freelancer/fiverr/linkedin.
- **`ai-os` CLI مُخترَق**: حزمة `octopus-linkedin` لها `cli.py` top-level في user site-packages. حزمة `aios` entry point كان `ai-os = "cli:main"` → `import cli` يحلّ لـ octopus-linkedin بدل aios (collision). نتيجة: `ai-os persona detect` وكل أوامر `ai-os` كانت تشتغل كأنها `octopus-linkedin`.

### الإصلاحات
- **`scripts/mcp_env_wrapper.py`**: على Windows استُبدل `os.execvpe` بـ `subprocess.run` (inherited handles). POSIX فضّل `execvpe` (أكفأ). ده أصلح كل MCP servers دفعة واحدة.
- **إعادة تسمية `cli.py` → `aios_cli.py`** (إصلاح دائم للـ collision): تحديث `pyproject.toml` (`ai-os = "aios_cli:main"`, `py-modules`), `tests/test_cli.py`, `install.ps1`/`install.sh` (shim + verification), `runtime/ci.py` + `eval/harness.py` (mypy targets), docs (README, README-AR, BOOTLOADER, MAINTENANCE_PROMPT, ACTIVE_CONTEXT). `pip install -e .` لإعادة توليد editable finder MAPPING + `ai-os.exe`.
- **التحقق**: linkedin MCP رجع 28 أداة + `get_profile` رجع بيانات Moataz Ahmed. `ai-os status`/`persona detect --multi` شغّال. ruff ✅, mypy ✅, `tests/test_cli.py` 23 passed.
- **ملاحظة**: `ai-os.exe` في `C:\Users\int190\AppData\Roaming\Python\Python314\Scripts` (user Scripts، ليس على PATH) — الـ WindowsApps shim `ai-os.cmd` هو اللي على PATH. لو الـ shim قديم بيشاور لـ `cli.py`، شغّل `install.ps1` لتحديثه لـ `aios_cli.py`.
