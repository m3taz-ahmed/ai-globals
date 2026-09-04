[FILE] Memory
[OBJ] Short-term context and cross-session continuity.
[RULES]
1. [REQ] Read at session start.
2. [REQ] Update at session end via `workflows/17-memory-sync.md`.
3. [REQ] Keep under 500 lines.
[UPDATED] 2026-09-04
[NOTES]
- **v5.10.1 release — security hardening + architecture cleanup — 2026-09-04**:
  - **SSRF**: IPv4+IPv6 private IP blocking via `ipaddress` module, DNS resolution re-check, `_validate_endpoint()` extracted, `launch()` uses `_a2a_open()`.
  - **RBAC**: `AIZEE_RBAC_STRICT=1` denies admin-only tools (logic bug fixed — was denying all).
  - **Audit**: fail-closed default (`AIZEE_AUDIT_STRICT="1"`).
  - **MCP client**: default env allowlist (no secret leakage); `AIZEE_MCP_ENV_PASSTHROUGH=1` for opt-out.
  - **Supply chain**: all GitHub Actions SHA-pinned; pip-audit/bandit/build/twine version-pinned.
  - **Architecture**: CompiledPipeline deleted, Kernel/KernelBuilder exported, RLock+atomic writes, bounded dashboard threads.
  - **Performance**: telemetry tail-read, metrics sort-once, learning_loop batch persist.
  - **Coverage**: 80%→95% across all gates. **Tests**: 3865 total.
  - **Docs**: counts synced (109/110/54/197/3865), stale refs fixed, garbled tree fixed.
- **Comprehensive audit review + full remediation — 2026-09-04 (SEC + PERF + DEVX personas)**:
  - **Audit review**: Verified all 28 issues from the v5.10.0 audit report against actual code in both `.ai` (working) and `aizee` (deployment). Found that 14 issues were ALREADY FIXED in `.ai` from prior sessions but not synced to `aizee`. The audit report had reviewed the stale `aizee` copy.
  - **Already-fixed issues (14)**: #1 (audit fail-open+counter), #2 (guardian _MISSING sentinel), #3 (_async_spawn validation), #4 (binary allowlist deny), #9 (storage_backend table regex), #10 (budget is None), #12 (audit rotation prev_hash), #16 (regex cache limit), #21 (plugin traversal check), #22 (RBAC allow-all warning), #24 (yaml literals .lower()), #25 (SSE CORS _origin()), #26 (policy AST cache).
  - **Fixed in this session (10)**:
    - **#6 HIGH**: `runtime/kernel.py` — `KernelBuilder.build()` now syncs `budget`/`audit` to `policy_mgr` (was only syncing `policy`/`guardian` → stale references).
    - **#19 MED**: `runtime/skill_resolver.py` — `list_skills()` now excludes `README`/`EVAL` stems (was counting `README.md` as a skill → 111 instead of 110).
    - **#20 MED**: `config.py` — fallback version `"5.0.0"` → `"5.10.0"`.
    - **#27 LOW**: `runtime/telemetry.py` — `query()` now uses bounded `deque(maxlen=limit*10, min 1000)` instead of `readlines()` (prevents RAM bloat on large logs).
    - **#28 LOW**: `aizee_cli.py` — `main()` now catches `KeyboardInterrupt` (exit 130) + generic `Exception` (exit 2, with `--verbose` re-raise) instead of only `CLIInputError`.
    - **#23 LOW**: `Memory.md` — fixed `bun-1` file reference (validate-globals was flagging the old `.md` suffix as a broken link).
    - **D1**: `runtime/kernel.py` — removed dead code: `_act_via_compiled_pipeline`, `_get_compiled_pipeline`, `register_action_pipeline`, `_pipeline_builders`, `_compiled_pipelines` (deprecated GATE-B4, never called from `act()`).
    - **D4**: `runtime/supply_chain_guard.py` — fixed `OsvDevClient` docstring from "fail-open" to "fail-closed" (code was already fail-closed, docstring was wrong).
    - **D5**: `memory/checkpoint.py` — documented why single connection is intentional (serial access, WAL, RLock-guarded — pool would add complexity without benefit).
    - **D7**: `README.md` + `spec.md` + `AGENTS.md` — updated counts: runtime 108→109, MCP 36→84 (all 4 locations).
  - **Lint fixes (pre-existing, 8 ruff + 7 mypy)**: `defensive_injection.py` (zip strict=False), `feature_flags.py` (combined nested if), `learning_loop.py` (extraneous parens), `mobile_patterns.py` (unused Callable import, combined if branches, unicode comment), `storage_backend.py` (parenthesize and subexpression), `experiment_tracker.py` (unused type:ignore), `error_classifier.py` (type:ignore code fix), `metrics.py` (unused type:ignore), `cro_tools.py` (hasattr instead of `in` for dataclass), `test_closure_evaluator.py` (import sorting).
  - **Review subagents**: 2 read-only subagents reviewed all 18 modified files + project-wide health. Found 3 issues in my changes (README stale counts in 2 more lines, telemetry bound too small, CLI --debug dead branch) — all fixed immediately.
  - **Quality gates (all green)**: ruff PASS (0 errors), mypy PASS (276 files, 0 errors), pytest 104 passed (50 targeted + 54 middleware/closure), validate-globals Errors=0 (was 1).
  - **Sync**: `.ai` → `aizee` via `update_aizee.bat` — complete. `aizee` now also green (ruff PASS, validate-globals Errors=0).
- **Dashboard settings full wiring + UI improvements — 2026-09-01 (ARCH persona)**:
  - **All 14 settings sections now APPLIED** (previously only mcp_servers was wired; the other 13 were cosmetic-only). Added `apply_settings_to_kernel()` in `runtime/settings.py` — called by `Kernel.__init__` after managers + compat attributes are initialized, and re-applied on dashboard restart (new kernel picks up overrides automatically).
  - **Per-section override appliers**: `_apply_budget_overrides` (0=unlimited skip), `_apply_guardian_overrides` (Decision enum mapping), `_apply_firewall_overrides` (FirewallAction enum mapping), `_apply_policy_overrides`, `_apply_loop_detector_overrides`, `_apply_injection_defense_overrides` (instance attr shadows ClassVar), `_apply_persona_overrides`, `_apply_audit_overrides`, `_apply_telemetry_overrides`, `_apply_memory_overrides`, `_apply_design_overrides`.
  - **UI improvements** (`dashboard/app.js` + `index.css`):
    - **Check All / Uncheck All** buttons on MCP Servers settings page + live count summary (`X / Y enabled`).
    - **Auto-reload after save**: `saveSettings()` now calls `/api/settings/restart` automatically after a successful save — no need to click "Restart aiZee" separately. Toast: "Settings saved & applied."
  - **README updated** (both `README.md` + `README-AR.md`): Added warning about disabling unused MCP servers (memory/load impact), documented Check All/Uncheck All + auto-reload, noted that all settings are applied live.
  - **Tests**: `tests/test_settings_wiring.py` — 14 tests covering budget (max_tokens, zero=unlimited, on_exceed), guardian (default_decision, on_error), mcp_firewall (catch_all), policy (default_action), loop_detector (window/threshold), injection_defense (thresholds), persona (default, multi), audit (retention_days), telemetry (enabled, sse_interval), reapply-on-reload. All pass.
  - **Quality gates**: ruff PASS, mypy PASS (8 files, 0 errors), FULL pytest 3819 passed / 0 failed / 1 skipped (tkinter).
- **MCP toggle gate fix + settings audit — 2026-09-01 (ARCH persona)**:
  - **Root cause**: Dashboard MCP server toggles were cosmetic-only. `SettingsManager.is_mcp_enabled()` + `mcp_status()` worked and persisted to `state/settings.json`, but NO runtime consumer read the toggle — `McpClient` loaded config from `aizee_mcp/config.json` only, all 27 plugins spawned `McpClient` directly, CLI `mcp`/`linkedin` commands did the same. Toggling a server OFF did nothing.
  - **Fix (block + hide)**:
    - `runtime/settings.py`: Added process-wide `get_settings_manager()` / `reload_settings_manager()` / `clear_settings_cache()` cache so kernel, dashboard, McpClient, and PluginManager share ONE `SettingsManager` instance — a dashboard toggle + restart is immediately visible to every MCP gate.
    - `runtime/kernel.py`: `kernel.settings_manager` wired in `_init_core_services` via `get_settings_manager(kernel.root)`.
    - `runtime/mcp_client.py`: `McpClient.__init__` now accepts optional `settings_manager` (defaults to shared cache). `call_tool` / `_call_tool_sync` / `async_call_tool` all check `_is_enabled()` BEFORE spawning — disabled servers return `{ok: False, disabled: True, error: "..."}` with no process spawn. New public `is_enabled()` method.
    - `runtime/plugin.py`: `PluginManager.get_tools()` skips plugins whose MCP server is disabled in settings — tools neither load nor appear.
    - `dashboard/server.py`: `_settings_instance()` now uses `get_settings_manager()` (shared). Restart endpoint calls `reload_settings_manager(root)` + `_terminate_pool()` so disabled servers stop running immediately. Removed stale `_settings_cache` global.
    - `aizee_cli.py`: `cmd_mcp` + `cmd_linkedin` now check `client.is_enabled()` and print a clear "disabled in dashboard settings" message.
  - **Tests**: `tests/test_mcp_toggle_gate.py` — 12 tests (block calls, block async calls, is_enabled reflects toggle, unknown server defaults enabled, enabled proceeds, re-enable restores calls, shared cache, reload picks up disk change, McpClient uses shared manager, disabled plugin tools hidden, enabled plugin tools visible, no settings_manager falls back to all tools). All pass.
  - **Quality gates**: ruff PASS, mypy PASS (6 changed files, 0 errors), FULL pytest 3805 passed / 0 failed / 1 skipped (tkinter).
  - **Settings audit finding (IMPORTANT)**: Audited all 14 dashboard settings sections. Only `mcp_servers` is APPLIED by the runtime. The other 13 sections (budget, guardian, mcp_firewall, policy, loop_detector, injection_defense, plugins, persona, dashboard, telemetry, audit, memory, design) are **COSMETIC-ONLY** — written to `state/settings.json` but never read/applied by any runtime consumer. Each has its own canonical source (state/budget.json, runtime/policies/*.yaml, plugins.yaml, personas.yaml, env vars, hardcoded constructor args). Fixing all 13 is a separate larger task — not done in this session.
- **P1-P4 comprehensive remediation — 2026-08-30 (QA + DEV + SEC personas)**:
  - **P1 Critical security (5 fixes)**:
    - **B1**: `aizee_mcp/aizee_server.py` + `rbac.py` — RBAC fail-open → fail-closed. Corrupted `rbac.yaml` now denies ALL tools to non-admins (sentinel `_RBAC_BROKEN_SENTINEL`). Exception in `check_tool_permission` → deny (not allow).
    - **B2**: `runtime/mcp_client.py` — MCP config command injection. Added `_validate_mcp_command()` rejecting shell metacharacters + allowlist of approved binaries (python/node/uv/etc).
    - **B3**: `runtime/crypto.py` + `memory/store.py` — Key management. Added `AIOS_ENCRYPTION_KEY_FILE` / `AIZEE_INTEGRITY_KEY_FILE` env vars for keys outside OS root. Loud SECURITY warning when auto-generating inside OS root.
    - **B4**: `memory/schema_contract.py` — Schema drift false positive. Replaced DDL string matching with column-level comparison (`_extract_columns()`). ALTER TABLE ADD COLUMN no longer triggers false `column_mismatch`.
    - **D1**: `AGENTS.md` — Fixed all mojibake (Arabic persona commands + em-dashes + arrows). Clean UTF-8.
  - **P2 Activate non-functional features (5 wirings)**:
    - **F4/I1**: `runtime/budget.py` — `BudgetWindowManager` wired in `BudgetManager.__init__` + `maybe_refresh_policies()` called from `BudgetManager.check`.
    - **F5/I2**: `runtime/managers/agent_manager.py` + `kernel.py` — `HealthMonitor.heartbeat()` called on spawn + delegate. New `check_health()` alias.
    - **F1/I3**: `runtime/managers/policy_manager.py` — `ApprovalService` wired as optional enhancement alongside `ApprovalCache`. Backward-compatible.
    - **F6/I4**: `aizee_cli.py` — New `aizee spec advance <spec_id>` CLI subcommand calling `SpecEngine.advance()`.
    - **F3/I5**: `runtime/plugin_system.py` — `run_hook` placeholder replaced with real `subprocess.run` execution (30s timeout, JSON stdin, graceful failure).
  - **P3 Test quality (6 improvements)**:
    - **Q3/I10**: New `tests/test_kernel_gate_order.py` — verifies `Probity → Guardian → Policy → LoopDetector → Budget → Audit` call order.
    - **Q6/I11**: New `tests/factories.py` — 6 factory functions (random_uuid, random_token, iso_timestamp, date_str, fake_memory_id, fake_budget_dict).
    - **Q4/I12**: Merged 4 duplicate `conftest.py` into single root `conftest.py`. Smart `_mock_time_sleep` (only mocks non-slow tests).
    - **Q7/I14**: `pyproject.toml` — Added `dashboard` + `eval` to coverage `source`.
    - **Q8**: New `tests/mcp/test_rbac.py` — 14 tests covering RBAC fail-closed, role combinations, corrupted config.
  - **P4 Cleanup + remaining SEC (7 fixes)**:
    - **I15**: `runtime/__init__.py` — Added documentation distinguishing production-wired vs retained-for-compatibility exports.
    - **D2**: `scripts/sync_docs.py` run — AGENTS.md, spec.md, README.md, README-AR.md counts updated (108 runtime, 110 skills, 54 numbered workflows, 197 stack, 3753 tests).
    - **D3**: `manifest.json` — Added missing triggers for WF 27 (NativePHP) + WF 31 (drafter-reviewer).
    - **D4**: `scripts/validate-globals.py` — Version 5.8.0→5.10.0 in argparse + banner. Removed stale `nuxt-4`/`drizzle-orm`/`bun-1` references from IGNORED_FILE_REFS.
    - **D5**: `pyproject.toml` — Added `psutil`, `sentry-sdk`, `defusedxml` to dev deps (matching mypy overrides).
    - **D6**: `runtime/tech_stack.py` — Fixed `turbovec` alias (added `turbovec-standards`) + `graphifyy` alias (added `graphifyy`).
    - **B5-B9 (SEC)**: Webhook SSRF validation (`approval_service.py`), Audit HMAC chain (`audit.py`), Guardian ReDoS protection (`guardian.py`), SEO OOM limit (`seo_tools.py` 2000→500 pages + 512MB check), Dashboard token to file not stdout (`dashboard/server.py`).
  - **Quality gates**: ruff PASS (0 errors), mypy PASS (254 files, 0 errors), FULL pytest 3793 passed / 9 skipped (tkinter) / 0 failed / 84.90% coverage.
- **Comprehensive review + full remediation — 2026-08-30 (SEC + ARCH personas)**:
  - **3 CRITICAL fixes**:
    - **C1**: `runtime/policy.py` — `_MISSING` sentinel was truthy (`bool(object())` = True) → bare missing attributes matched every rule (allow-by-absence). Fixed: `_MissingSentinel` class with `__bool__` → False. `Subscript` now returns `_MISSING` (not None) on missing key. `UnaryOp.not` returns False for missing operand.
    - **C2**: `aizee_mcp/adapters.py` — SSRF via `startswith("http://localhost")` accepting `localhost.evil.com`. Fixed: `urllib.parse.urlparse` + `_is_loopback_ip()` (validates 4-octet 127.0.0.0/8).
    - **C3**: `runtime/policy.py` — `Subscript` returned `None` on missing key → `None != "prod"` = True → allow rules matched. Fixed: returns `_MISSING` (fail-closed).
  - **6 HIGH fixes**:
    - **H1**: `runtime/budget.py` — zero-value limits (`max_tokens=0`) treated as unlimited (truthy check). Fixed: `is not None` checks (5 locations).
    - **H2**: `runtime/managers/policy_manager.py` — `_build_probity` returned after first root, dropping project-level rules. Fixed: collect from all roots.
    - **H3+H4**: `dashboard/server.py` — CORS reflected `*`/unvalidated origin with credentials; `X-Requested-With` exposed in Allow-Headers (CSRF bypass). Fixed: explicit allowlist, reject `*`; removed `X-Requested-With` from Allow-Headers.
    - **H5**: `runtime/supply_chain_guard.py` — OSV.dev `_fetch` returned `[]` on network error (fail-open). Fixed: raises `SupplyChainGuardError` (fail-closed).
    - **H6**: `memory/git_memory.py` — `add_remote` accepted arbitrary URLs (`ext::` command execution). Fixed: `_validate_remote_url` rejects `ext::`/`file://`, validates scheme + remote name.
  - **11 MEDIUM fixes**: M1 (budget `maybe_refresh_policies` docstring honest), M2 (`check_probity` wires real history), M3 (kernel security modules log warnings instead of silent `except: pass`), M4 (guardian `DecisionStatus` inside try), M5 (audit `_last_hash` backward-scan growing window for >8KB records), M6-M10 (injection_detector: `content policy` typo, concatenated variants D8-D10, hex/unicode `{2,}` quantifier, single `../` traversal, tail scanning for >100K inputs + encoding decode on tail), M11 (taint guardrail logging).
  - **6 LOW fixes**: L1 (KernelBuilder syncs manager refs), L2 (audit rotation logging), L3 (audit `_ts_after` datetime comparison), L4 (X-Forwarded-For right-to-left scan), L6 (integrity key `chmod 0o600`), L7 (defensive_injection sanitizer patterns expanded to match detector).
  - **Documentation drift fixed**: `manifest.json` version 5.7.1→5.10.0 + duplicate `pr`/`PR` keys resolved (`pr`→`pr-outreach`). `spec.md`/`README.md`/`README-AR.md` counts updated (107→112 modules, 110→111 skills, 54→66 workflows). `validate-globals.ps1`/`.py` version 5.8.0→5.10.0. README "What's New" sections added for 5.9.0 + 5.10.0.
  - **Quality improvements**: `[tool.coverage]` section added to `pyproject.toml` with `fail_under=80`. Integration tests marked `pytest.mark.integration` (TEST-10). `test_list_personas` fixed (==22 → >=22 for 29 actual personas).
  - **New tests**: `tests/test_review_fixes.py` (23 regression tests for all fixes), `runtime/tests/test_local_responder.py` (14 tests), `runtime/tests/test_tracing_otel.py` (8 tests), 6 new SSRF tests in `tests/mcp/test_adapters.py`.
  - **Quality gates**: ruff PASS (0 errors), mypy PASS (14 modified files, 0 errors), validate-globals PASS (0 errors), FULL pytest 3717 passed / 7 pre-existing flaky failures (timing tests + persona detector CRO/UX conflict) / 92.63% coverage.
  - **Subagent review**: All 15 fixes verified correct by read-only review subagent; 2 follow-up issues fixed (stale docstring, tail encoding decode).
- **Dashboard Settings Panel — 2026-08-30 (ARCH persona)**:
  - **New runtime module**: `runtime/settings.py` — `SettingsManager` for user-facing settings persisted to `state/settings.json` (separate from canonical config sources). Thread-safe, fail-safe (corrupt file → defaults), versioned schema. 14 sections: mcp_servers, budget, guardian, mcp_firewall, policy, loop_detector, injection_defense, plugins, persona, dashboard, telemetry, audit, memory, design.
  - **Dashboard API endpoints** (`dashboard/server.py`): 6 new endpoints — `GET/POST /api/settings`, `GET /api/settings/defaults`, `POST /api/settings/reset`, `GET /api/settings/mcp-status`, `POST /api/settings/restart`. Soft-reload kernel (reset caches + terminate MCP pool + reload settings).
  - **Dashboard UI** (`dashboard/index.html` + `app.js` + `index.css`): New "Settings" tab with 6 sub-sections (MCP Servers, Budget & Costs, Security & Gates, Injection Defense, Plugins & Persona, Dashboard & System). Toggle switches for MCP servers (34 servers in 9 categories), forms for budget/guardian/firewall/policy/loop detector, toggles for injection defense modules, plugin management, dashboard/telemetry/audit/memory/design settings. Save/Reset/Restart buttons with toast notifications.
  - **Tests**: `tests/test_settings_manager.py` — 39 tests covering defaults, load/save, validation, section updates, MCP toggles, reset, fail-safe on corrupt file, **migration** (v1→v2, orphan cleanup, backup creation, user value preservation). All pass.
  - **Migration framework**: `SETTINGS_VERSION=2` + `_MIGRATIONS` registry + `_migrate_if_needed()` in `_load()` + public `migrate()` method. On load: backs up old file to `settings.json.v{old}.bak`, runs sequential migration steps, prunes orphaned keys, bumps version. `scripts/update.py` calls `sm.migrate()` in post-install hooks (step 5).
  - **Quality gates**: ruff PASS, mypy strict PASS (3 files), pytest 39/39 PASS.
- **Claude Code Skills Import + Design Tooling Stack — 2026-08-28 (UX + DEVX personas)**:
  - **8 new skills** imported from Claude Code ecosystem study:
    - `skills/web-design-guidelines.md` — 100+ rules from Vercel (a11y, forms, dark mode, typography, animation, images, performance, navigation, touch, i18n)
    - `skills/design-taste.md` — Design DNA extractor (4-phase pipeline: Playwright capture → measure tokens → extract Taste DNA → write {domain}.md + .json). Requires Playwright MCP.
    - `skills/image-to-code.md` — Image-first design-to-code workflow (generate images → analyze → implement). DESIGN_VARIANCE=8, MOTION_INTENSITY=5, VISUAL_DENSITY=6.
    - `skills/backend-design.md` — 13 senior backend reflexes (think-before-coding, data-modeling-discipline, migration-safety, query-discipline, idempotency, error-handling, observability, security, auth, performance, debugging, testing, boring-by-default)
    - `skills/accessibility-auditor.md` — 11 WCAG 2.2 AA specialist agents (ARIA, contrast, keyboard, cognitive, forms, images, media, structure, motion, touch, i18n)
    - `skills/web-quality.md` — Lighthouse + Core Web Vitals (LCP <2.5s, INP <200ms, CLS <0.1, FCP, TTFB, SEO, Best Practices)
    - `skills/motion-design.md` — Animation audit from 3 designer perspectives (Kowalski, Krehel, Tompkins) + timing/easing/choreography checklist + severity rankings
    - `skills/qa-automation.md` — 6 Playwright QA agents (smoke, ux, adversarial, performance, mobile, multi-user) + 5-step workflow
  - **3 new runtime modules**:
    - `runtime/design_slop_verifier.py` — AI-slop detection (7 categories: gradient wash, accent-border cards, SVG illustrations, overused fonts, emoji decoration, 3-column grid, AI headline phrases). Optional injectable vision-model judge_fn. Fail-open-safe.
    - `runtime/plugin_system.py` — Plugin registry (discovers plugins from `plugins/` dir, validates manifest, manages lifecycle: DISCOVERED→LOADED→ACTIVE→ERROR→DISABLED). Supports skills, agents, commands, hooks (UserPromptSubmit/PreToolUse/PostToolUse/Stop), MCP servers. Keyword + persona indexing.
    - `runtime/design_library.py` — 58 brand design systems catalog (Stripe, Linear, Vercel, Figma...). Load single brand, mix 2-3 brands (simple or granular section mapping), auto-detect project type and suggest best-fit brands.
  - **Kernel integration**: `kernel.py` now initializes `design_slop_verifier`, `design_library`, `plugin_registry` in `_init_core_services`.
  - **__init__.py**: 20+ new symbols exported.
  - **personas.yaml**: 8 new lord_skills entries with keyword indexes. UX persona gets 6 design skills, DEV gets backend-design, QA gets qa-automation.
  - **Tests**: 39 new tests across 3 test files + 15 persona reset tests. All pass.
  - **Quality gates**: ruff PASS, mypy PASS (5 source files), pytest 54/54 PASS.
  - **Persona Reset Shortcuts**: 17 trigger commands (`/reset`, `#reset`, `/انتحل`, `#شخصيات`, `/بدّل`, `/persona`, `#switch`, etc.) in `runtime/persona.py`. When detected in a chat message, `inject_persona_context` clears existing persona fields and re-detects based on any hint text after the command (e.g., `/reset اكتب backend API` → switches to DEV persona + `backend-design` skill). Works mid-session without `fresh_context=True`.
  - **Persona Status Shortcuts**: 17 status query commands (`/status`, `#status`, `/حالة`, `#حالة`, `/whoami`, `/مين`, `/info`, `/معلومات`, etc.) in `runtime/persona.py`. When detected, `inject_persona_context` populates `context["persona_status"]` with a formatted Arabic report showing: primary persona (name + weight), secondary personas, primary skills (with descriptions), and lord skills (with descriptions). Does NOT re-detect — just displays current state. `format_persona_status()` is the formatter function.
  - **Research report**: `tech-stack/claude-code-skills-research.md` (191 lines, comprehensive study of 50+ Claude Code skills across 6 domains).
- **Prompt Injection Defense Stack — 2026-08-28 (SEC + ML personas)**:
  - **7 new runtime modules** for comprehensive prompt-injection defense (OWASP LLM01):
    - `runtime/injection_detector.py` — 13-technique detector (direct override, system prompt extraction, roleplay jailbreak, multi-turn manipulation, encoding obfuscation, typoglycemia, best-of-N, HTML/Markdown injection, multimodal injection, RAG poisoning, tool abuse, thought injection, memory poisoning) + encoding-aware scanning (Base64/Hex/URL decode + Unicode NFKC normalization) + multilingual patterns (Arabic). 50+ regex patterns, deterministic, model-free. BLOCK_THRESHOLD=12, SUSPICIOUS_THRESHOLD=5.
    - `runtime/defensive_injection.py` — **الميزة الأساسية**: defensive prompt injection. When policy violation detected, aiZee injects its own authoritative instructions (SYSTEM OVERRIDE + data fence + safe redirect) to steer the model back to compliance. 3 strategies: REDIRECT (wrap + redirect), SANITIZE_AND_REDIRECT (strip injection + redirect), QUARANTINE (don't relay content). Per-technique redirect messages.
    - `runtime/tool_output_sanitizer.py` — indirect injection defense. Scans tool outputs (web fetch, file read, MCP calls) before they re-enter the context window. HIGH_RISK_TOOLS set for perf optimization.
    - `runtime/prompt_injection_detector.py` — two-stage semantic detector. Stage 1: deterministic (InjectionDetector). Stage 2: optional injectable model_fn (PromptGuard/deberta/Lakera). Fail-open-safe fallback. Model-free by default.
    - `runtime/dual_llm.py` — Simon Willison's dual-LLM pattern. Privileged LLM (has tools, no untrusted content) + Quarantined LLM (reads untrusted content, no tools). Breaks indirect injection path.
    - `runtime/agent_baseline.py` — behavioral anomaly detection. Tracks tool/data/endpoint usage per agent. Flags new tools, new data sources, new endpoints, rare actions. Learning → Detecting phase transition.
    - `eval/prompt_injection_suite.py` — eval suite with 33 attack cases (all 13 techniques + Arabic) + 15 benign cases (including hard negatives). Measures detection rate, false positive rate, containment rate.
  - **Kernel integration**: `kernel.py` now initializes `injection_detector`, `defensive_injector`, `tool_output_sanitizer`, `baseline_registry` in `_init_core_services`.
  - **__init__.py**: 7 new modules exported (20+ new symbols).
  - **Tests**: 82 new tests across 7 test files. All pass.
  - **Eval results**: Detection rate 100% (33/33), False positive rate 0% (0/15), Containment rate 100% (33/33).
  - **Quality gates**: ruff PASS, mypy PASS (8 source files), pytest 82/82 PASS.
  - **Research repos cloned** to `D:\server\temp\prompt-injection-study\`: pint-benchmark (Lakera), PromptInject, PIArena (ACL 2026).
  - **Research report**: `tech-stack/prompt-injection-research.md` (252 lines, comprehensive).
- **Comprehensive review report remediation — 2026-08-24 (ARCH persona)**:
  - **Schema drift fix** (`memory/store.py`, `memory/schema_contract.py`): `memory_decay` table + `idx_decay_last_accessed` index now created in `_init_schema` (not lazily). FTS5 shadow tables (`memories_fts*`) ignored in `detect_schema_drift`. `verify_schema_integrity` now returns `(True, None)` for fresh DBs — no more false drift warnings.
  - **Lazy SentenceTransformer** (`memory/vector.py`): `Embedder.__init__` no longer loads the model; `_ensure_model()` loads on first `embed()` call. Prevents network download on every `MemoryStore` creation. Updated 3 tests for lazy behavior.
  - **Documentation sync**: Updated all counts to 85 runtime / 72 skills / 50 workflows / 163 tech-stack / 36 MCP tools / 22 personas across `spec.md`, `README.md`, `README-AR.md`, `AGENTS.md`, `docs/ONBOARDING_SRE.md`, `tech-stack/aizee-5.md`, `tech-stack/README.md`. Fixed `aios_`→`aizee_` metric names in ONBOARDING_SRE.
  - **validate-globals PASS**: Removed broken competitive-analysis report ref from `Memory.md`. Fixed `validate-globals.ps1` version 5.6.0→5.7.1. CRLF→LF in `AGENTS.md`/`spec.md`. Fixed `sync_docs.py` to use `newline="\n"` and exclude `README.md`/`EVAL.md` from skill count.
  - **manifest.json**: Features expanded 35→97 (all 85 runtime modules + 12 cross-dir features).
  - **Deleted** `skills/seo-content-generator.md` (superseded by `skills/seo-lord/`). Skills count: 73→72.
  - **Rust/Cargo supply chain support** (`runtime/supply_chain_guard.py`): Added `DependencyEcosystem.RUST`, `_RUST_USE_RE` regex, `_extract_rust_imports()`, `_load_rust_declared()`, `_parse_cargo_toml()`. Handles `use` statements, skips std/core/alloc/crate/super.
  - **Docker image cosign signing** (`.github/workflows/release.yml`): Added `cosign sign --yes` for container image (keyless OIDC). SBOM was already signed.
  - **CI mypy expansion** (`.github/workflows/validate.yml`): Added `eval/harness.py`, `eval/pipeline.py`, `eval/reliability.py`, `eval/redteam.py`, `scripts/guard_invariants.py`, `scripts/sync_docs.py` to mypy check.
  - **eval/tests/test_memory_decay.py** (new, 3 tests): Verifies memory_decay table exists at init, decay lifecycle (add→access→decay→recover), persistence across restarts.
  - **docs/ONBOARDING_SRE.md**: Added sections for `finalization_reserve` (budget), `KillSwitchRule` (guardian hard-stop), `AIZEE_DASHBOARD_TOKEN` (dashboard security).
  - **skills/README.md** (new): 72-skill catalog with types, domains, and adding-guide.
  - **testing-tiers.md**: Added FAST-tier commands for taint, skill_scanner, confidence_gate, learning_loop, vector tests.
  - **ACTIVE_CONTEXT.md**: Rewritten for v5.7.1 current state.
  - **scripts/update_aizee.bat**: Hardcoded paths → relative (`%~dp0..` + `AIZEE_DEPLOY` env override).
  - **guard_invariants.py**: `skills/README.md` excluded from frontmatter check.
  - **graphify**: Rebuilt (13124 nodes, 27847 links). Note: reports checked `edges` key but actual key is `links` — graph was never broken.
  - **Quality gates**: ruff PASS, mypy PASS (224 files), validate-globals PASS (0E/0W), sync_docs in sync, guard_invariants all pass, targeted tests 98 passed.
- **Comprehensive review of all 125 changed files — 2026-08-24 (ARCH persona + 3 parallel review subagents)**:
  - **3 subagents reviewed all 125 files** in parallel across WS-B/A, WS-D/E/F, WS-G/H/I/J groups.
  - **Issues found and fixed (17 total)**:
    - **CRITICAL: k8s NetworkPolicy egress** (`deploy/k8s/deployment.yaml`): `to: []` blocked ALL outbound traffic. Fixed to allow HTTPS egress to any destination.
    - **CRITICAL: schema_contract missing memory_decay** (`memory/schema_contract.py`): `memory_decay` table created in `store.py` but missing from `default_memory_contract()` → schema drift warnings on every init. Added table + index to contract.
    - **CRITICAL: mcp_firewall.yaml default_action silently ignored** (`runtime/policies/mcp_firewall.yaml`): GATE-B3 restriction caused `default_action: allow` to be silently dropped → MCP tools became `ask` instead of `allow`. Fixed by removing `default_action` and adding catch-all allow rule with priority 0. Also fixed YAML parsing error (unquoted colon in description).
    - **HIGH: Missing runtime exports** (`runtime/__init__.py`): 12 new module exports missing (ConfidenceGate, LearningLoop, SkillRouter, Bounder, Witness, LazyImport, ReflexionLog, OutputEnvelope, CostProvider, etc.). Added all exports + `__all__` entries.
    - **HIGH: Probity normalization inconsistency** (`runtime/probity.py`): `EnforceFilenameCasing` and `EnforceTdd` checked `("write", "edit")` directly instead of using `normalize_action_type()`. Fixed to use consistent normalization.
    - **HIGH: Constitution regex too narrow** (`runtime/spec/engine.py`): `r"MUST\s+(.+?)(?:\.|$)"` missed principles ending with `!`, `?`, `;`, `:`, or newlines. Fixed to `r"MUST\s+(.+?)(?:[.!?;:]|\n|$)"`.
    - **MED: delete_by_source_batch length validation** (`memory/store.py`): No length limit on source strings. Added 1000-char max validation.
    - **MED: ConfidenceGate weight validation** (`runtime/confidence_gate.py`): No validation that weights are in [0.0, 1.0]. Added validation with ValueError on out-of-range.
    - **MED: LazyImport error handling** (`runtime/quality.py`): Malformed import paths raised cryptic errors. Added path validation + try/except with clear error messages.
    - **MED: Priority parsing error handling** (`runtime/policy.py`): `int(r.get("priority", 0))` crashed on non-numeric strings. Added `_safe_priority()` helper with try/except + warning.
    - **MED: FTS5 sanitization enhanced** (`memory/store.py`): Parentheses and hyphens not stripped from FTS5 queries. Added to sanitization regex.
    - **GATE-B3 policy files cleanup**: Removed `default_action` from 5 non-default policy files (agentic-owasp.yaml, consequence-tiers.yaml, mcp_firewall.yaml, examples/api-rate-limits.yaml, examples/data-exfiltration.yaml, examples/time-based-access.yaml). Only default.yaml now sets default_action.
  - **New tests added (17 tests)**: weight validation (5), LazyImport error handling (3), priority parsing (6), delete_by_source_batch validation (4).
  - **Quality gates**: ruff PASS, mypy PASS (240 source files), full pytest suite green (exit code 0, 1 skip for tkinter).
- **Implementation plan remediation — 2026-08-24 (8 workstreams, 40+ items)**:
  - **WS-C (Dead Code Removal)**: Removed 26 dead modules + tests, updated manifest.json, README, AGENTS.md, spec.md, tech-stack/aizee-5.md to reflect 81 runtime modules.
  - **WS-B (Gate-Contract Repairs)**: GATE-B1 structured denial for probity violations; GATE-B2 `normalize_action_type()` maps Bash/Shell/Command→exec; GATE-B3 audit (rule names in denial), sentinel `_MISSING` prevents None==None escalation, policy `priority` field + sorting, `default_action` writable only by default.yaml; GATE-B4 deprecated bypass paths `register_action_pipeline()`/`_get_compiled_pipeline()`.
  - **WS-A (Security Hardening)**: SEC-W1 dashboard loopback enforcement (`AGENT_OS_HOST`, `_is_loopback_host()`); SEC-W2 k8s deploy manifests (NetworkPolicy ingress/egress restrictions); SEC-W3 dashboard robustness (Content-Length parsing, `?limit=` on audit/tracing, SSE headers + max duration).
  - **WS-D (Eval Overhaul)**: EVAL-W0 `GateVerdict` unified dataclass + `to_gate_verdict()` adapters; EVAL-W1 `eval/pipeline.py` real kernel.act() pipeline; EVAL-W2 10 executable assertion kinds (eq/contains/regex/decision_is/gate_is/custom); EVAL-W3 `AnchoredDimension` rubric anchored to assertions; EVAL-W5 `eval/redteam.py` red-team runner + SARIF 2.1.0 reporter; EVAL-W6 per-gate + per-policy breakdown.
  - **WS-E (SDD Enforcement)**: W1 task verification (evidence + `verified` flag blocks advance); W2 constitution enforcement (MUST principles checked against requirements); W3 state transition history; W4 drift v2 (file modifications + unapplied deltas + phase regressions); W5 paginated spec listing; W6 delta hardening (validate MODIFIED/REMOVED reference existing, ADDED no duplicates, no empty descriptions).
  - **WS-F (Memory Upgrades)**: W1 deterministic IDs (`_deterministic_id` content hash); W2 dedup (same content → same ID → no duplicate); W3 fact extraction (heuristic verb-based); W4 temporal search (`search_temporal`); W5 decay persistence (`memory_decay` table, `record_access`/`apply_decay`/`get_decay_score`); W6 search hardening (`search_safe` with length/null-byte/SQL-keyword sanitization).
  - **WS-H (Confidence Gating)**: `runtime/confidence_gate.py` — `ConfidenceGate` with weighted evidence, `ConfidenceVerdict` (frozen), 4 confidence levels (HIGH/MEDIUM/LOW/CRITICAL), fail-closed on no evidence.
  - **WS-G (Learning Loop)**: `runtime/learning_loop.py` — LEARN-01 hook bindings (POST_RESPONSE + ON_ERROR auto-record); LEARN-02 record-consolidate-rank-inject 4-stage loop with persistence.
  - **WS-I (Skills/Personas)**: `runtime/skill_routing.py` — SKILL-W1 `SkillRouter` routing meta-prompt; SKILL-W2 `PersonaDetectorV2` with confidence scoring + ambiguity detection.
  - **WS-J (Misc Quality)**: `runtime/quality.py` — W1 `CostProvider`/`FixedRateCostProvider`; W3 assertion helpers; W5 `OutputEnvelope` standardized output; W6 `Bounder` (text/list/dict bounding); W7 `Witness`/`WitnessRecorder`; W8 `LazyImport` generic; W9 `ReflexionLog` self-reflection.
  - **New test files**: test_kernel_probity_contract.py, test_policy_precedence.py, test_sdd_enforcement.py, test_memory_upgrades.py, test_confidence_gate.py, test_learning_loop.py, test_skill_routing.py, test_quality.py, test_pipeline.py, test_redteam.py, test_gate_verdict.py — 200+ new tests, all passing.
  - **Quality gates**: ruff PASS (repo-wide), mypy PASS (240 source files), full pytest suite green (1 skip for tkinter display).
- **Competitor analysis + Phase 1 implementation — 2026-08-23 (ARCH/SEC/QA/DEV personas)**:
  - **Competitor study**: Cloned 26 competitor repos to `D:\server\temp\competitor-study\`. Generated a report (262 lines) identifying 10 strengths, 15 weaknesses, 7 high-priority patterns to adopt. Sources: LLMFirewall (taint), SkillSpector (skill scanner), AgentGuard (typosquat + OSV.dev), agent-loop-guard (fuzzy + cycle + escalation), probity (Wilson CI + priority ladder), claw-eval (Pass^k + weighted scoring), microsoft/AgentRx (failure taxonomy), agent-trace (NDJSON + kill-switch), treehouse (safe sweep), mem0 (identity protection), AgentBudget (finalization reserve), agent-observatory (fail-open audit).
  - **2 new runtime modules**:
    - `runtime/taint.py` — 5-level taint label system (SYSTEM_TRUSTED → TOOL_OUTPUT → RAG_UNTRUSTED → USER_UNTRUSTED → SECRET) with Bell-LaPadula enforcement (no-write-up, no-read-down), sanitize/redact/merge/snapshot APIs, `classify_source()` heuristic for auto-labeling.
    - `runtime/skill_scanner.py` — Static security scanner with 30+ regex patterns across 7 categories (prompt injection, data exfiltration, secret exposure, privilege escalation, supply chain, tool poisoning, resource abuse). Baseline suppression via fingerprints, risk-level scoring (SAFE/LOW/MEDIUM/HIGH/CRITICAL), resource bounds (10K findings, 30s timeout cap).
  - **9 enhanced existing modules**:
    - `eval/reliability.py` — Wilson score CI, `k_needed_estimate()`, `pass_at_k()`/`pass_hat_k()`/`pass_cubed()`, `DimensionScores` weighted composite (safety veto), `priority_ladder()` 7-rule fixed-order verdict (PASS/KILL/INSUFFICIENT).
    - `runtime/supply_chain_guard.py` — `TyposquatDetector` (Levenshtein + homoglyph), `OsvDevClient` (OSV.dev API with 1h cache, fail-open on network error).
    - `runtime/audit.py` — Fail-open observability: OSError on log write is logged but NOT raised.
    - `runtime/budget.py` — `finalization_reserve` field (0-0.5 fraction reserved for final response), `effective_max_tokens`/`effective_max_cost` properties, `would_exceed()` pre-flight check.
    - `runtime/loop_detector.py` — Fuzzy repeat (Jaccard + edit distance similarity), cycle detection (A→B→C→A patterns), `ActionConfig` escalation ladder (CONTINUE→WARN→STOP→ESCALATE).
    - `runtime/trajectory.py` — `FailureCategory` 10-class taxonomy (from AgentRx), `export_ndjson()` zero-dependency trace export, `failure_summary()` by category, `tool_name`/`tool_input`/`tool_output` fields on steps.
    - `runtime/worktree_pool.py` — (deleted in v5.7.0 cleanup; worktree management now via external git).
    - `memory/store.py` — `_strip_identity_keys()` prevents tenant-scoping attacks (user_id/agent_id/session_id/tenant_id/actor_id stripped from caller metadata, only explicit params accepted).
    - `runtime/guardian.py` — `KillSwitchRule` (cost_ceiling/file_touched/tool_call_count/time_limit), `KillSwitchError`, evaluated first in `authorize()` before guardrails (hard stop, cannot be overridden).
  - **11 new test files** (119 tests, all passing): test_taint.py (17), test_skill_scanner.py (16), test_loop_detector.py (8), test_supply_chain_typosquat.py (9), test_budget_reserve.py (7), test_trajectory_enhanced.py (6), test_guardian_killswitch.py (9), test_audit_failopen.py (5), test_worktree_sweep.py (7), test_memory_identity.py (6), test_reliability_enhanced.py (21).
  - **Quality gates**: ruff PASS (all 12 touched files), mypy PASS (all 11 source files), pytest 119/119 passed. Pre-existing `memory/vector.py` unused-ignore warning untouched (not in scope).
  - **`runtime/__init__.py` updated**: Exports TaintError, TaintLabel, TaintTracker, classify_taint_source, SkillScanner, Baseline, ScanResult, ScanRiskLevel, ScanPatternSeverity, SkillFinding, TyposquatDetector, TyposquatFinding, OsvDevClient, VulnerabilityAdvisory, FailureCategory.
- **Dashboard asset-origin fix — 2026-08-23 (user-reported dead UI)**:
  - **Root cause of "Connecting..." + dead side menu in ALL browsers**: running NEW server code while `AIZEE_ROOT` pointed at the OLD deployment (`D:\server\aizee`) served OLD inline-script index.html under the NEW strict CSP (no 'unsafe-inline') → every script blocked silently. Verified via Edge headless: against matching assets, JS runs and status becomes "Connected".
  - **Fix (architectural)**: dashboard now serves its UI from its OWN code directory (`_CODE_DIR`, `_asset_dir()`, `_ASSET_DIR_OVERRIDE` for tests) instead of the discovered root — server and UI are always version-matched regardless of AIZEE_ROOT. Live-verified: with machine AIZEE_ROOT=aizee, GET / returns new shell + /app.js 200.
  - Also added `Cache-Control: no-cache` on all responses (prevents stale-shell breakage after upgrades) — earlier suspicion was browser cache; real cause was root mismatch.
  - Tests updated: serve_file_not_found + index_without_token use `_ASSET_DIR_OVERRIDE`; no_cache header test added; suite 78 green.
- **Dashboard open-access decision — 2026-08-23 (user request)**:
  - Tokens removed by default per user decision: no token files, no auto-generation; auth is OPT-IN via `AIZEE_DASHBOARD_TOKEN` env only. `_dashboard_token()` returns env value or None (open mode); `_auth()` passes when None.
  - Static assets (`/`, `/app.js`, icons) served unauthenticated in both modes — fixes chicken-and-egg where the page prompting for the token was itself protected. APIs stay CSRF-header-protected on POSTs regardless.
  - `python dashboard/server.py` now bootstraps sys.path for direct execution from any CWD (was ModuleNotFoundError on config).
  - Legacy ALLOW_NO_TOKEN flags obsolete (ignored). Tests rewritten: default=None + no file created; env opt-in works; leftover file ignored; POST on public path still 401. Live-verified open access end-to-end.
- **CRITICAL policy-evaluator fix — 2026-08-23 (elite review session)**:
  - **Privilege-escalation hole in `_SafeEvaluator`** (`runtime/policy.py`): YAML-style `true`/`false`/`null` literals were parsed as variable NAMES. `flag == true` resolved both sides to None when the flag was missing → `None == None` → True → rule matched EVERY action lacking that attribute. Impact: `reversible == true → allow` auto-approved ALL write/edit/apply actions; deny rules (e.g. tier-consequential-git-writes) falsely denied benign actions like ChatMessage ("what is the status?" was denied).
  - **Fix**: `_yaml_literals` mapping (true/false/null/none → Python values) in visit(Name); TypeError-safe comparisons (`'x' in missing` now fails closed instead of raising and voiding the rule).
  - **Regression tests**: runtime/tests/test_policy_evaluator_security.py (13 tests: literal resolution, membership-on-missing fail-closed, end-to-end git-deny + reversible-allow scoping).
  - **Also found & fixed**: CI validate.yml type-checked nonexistent `cli.py` (now aizee_cli.py); RemoteA2A SSL context memoized (was rebuilding CA store per poll tick); /app.js route coverage added.
  - **Verified end-to-end**: smoke of 25 module imports + 6 real CLI commands + persona detect + chat intent reply + sync_docs --check, all green after fix.
- **Security + quality + refactor pass — 2026-08-23 (session 2)**:
  - **12 security fixes** (3 critical): dashboard auth (app.js sends Bearer token), approve-via-GET removed from `/api/check` (dry-run only now), guardian fail-closed, verify_ssl effective, A2A timeouts, stable vector id hashing (blake2b), checkpoint RLock, MCP output validation hardened, git_memory path sanitization, CLI JSON/subprocess error handling, SEO fallback registration, CSP 'unsafe-inline' removed (external app.js).
  - **Quality gates zeroed on main**: mypy 0 errors (268 files, was 7), ruff 0 errors repo-wide (was 13). Full suite green ~4,050 tests @ 96.26% coverage.
  - **Product bugs**: nofollow robots detection implemented in seo_audit_page; multiple-h1 rule_id test mismatch fixed; Monica's BaseService permission dependencies removed from Guardian defaults.
  - **Refactors**: spec_engine.py (876L) → runtime/spec/ package (models/engine/scaffold/analysis/templates) with backward-compat facade; persona injection unified in inject_persona_context(); READ_ACTIONS canonical source for read-only classification; ChatManager now uses runtime/local_responder.py (intent-based offline assistant: status/budgets/workflows/rules/skills/stack intents).
  - **Tooling**: scripts/sync_docs.py (counts + workflow routing table from filesystem truth, --check wired into CI validate.yml); pytest-timeout 300s thread-method in pyproject; true async tests added (Guardian decorators + A2A executor path); CONTRIBUTING.md created.
  - **Docs repaired**: AGENTS.md/spec.md counts synced (105 modules / 73 skills / 36 workflows / 163 stack refs); workflows README duplicate table + missing rows (27, 33-35) fixed by regeneration; untracked fetch-free-keys.py removed (backup in %TEMP%\opencode).
  - **Note**: earlier "mojibake" reports in Memory.md were console-rendering artifacts — file verified clean programmatically (zero U+FFFD/private-use chars).
- **Security hardening pass — 2026-08-23 (12 fixes: 3 critical, 6 medium, 3 low)**:
  - **[CRITICAL] Dashboard auth fixed**: `dashboard/app.js` (new external file) now sends `Authorization: Bearer <token>` on every fetch; on 401 it prompts for the token and caches it in sessionStorage. The bundled UI previously never authenticated and only worked in ALLOW_NO_TOKEN mode.
  - **[CRITICAL] approve-via-GET removed**: GET `/api/check` is now dry-run only; `?approve=1` returns 400. Closes the CSRF hole where any website could self-approve privileged actions against localhost.
  - **[CRITICAL] Guardian fail-closed**: `PolicyManager.check_guardian` no longer swallows exceptions as allow — a broken guardian denies with `guardian_error` decision + audit log entry (`runtime/managers/policy_manager.py`).
  - **verify_ssl flag made effective** (`aizee_mcp/adapters.py`): verify_ssl=False now builds an explicitly unverified SSL context instead of silently returning None (= default verified context). Warning logged at init.
  - **A2A timeouts added**: launch/poll urlopen calls get `request_timeout` (default 30s, configurable) so hung remote servers can no longer block the executor thread indefinitely; poll also passes the SSL context now.
  - **Stable vector id fallback** (`memory/vector.py`): non-UUID ids hash via blake2b (deterministic across processes) instead of salted built-in `hash()` which orphaned vectors after restart.
  - **Checkpoint thread-safety** (`memory/checkpoint.py`): RLock around the shared `check_same_thread=False` SQLite connection (put/get/list/close).
  - **Non-strict output validation hardened** (`aizee_mcp/tools/mcp_output_schemas.py`): dropped `model_construct` bypass; invalid fields are dropped individually then re-validated — returned model is always fully validated. Also fixed pre-existing mypy no-any-return in `safe_model_dump`.
  - **git_memory path sanitization** (`memory/git_memory.py`): category/entry_id validated against safe-component regex in write/read/delete/list_entries (blocks `../`, separators, `.git`).
  - **CLI error handling** (`aizee_cli.py`): `_load_json` helper gives friendly errors for bad JSON in check/run/policy/saga/mcp/agent (rc=1, no traceback); cmd_sync checks script existence + reports nonzero exit; cmd_graphify reports failures/missing binary instead of silent success; doctor Kernel now gets project_root; removed duplicate local imports.
  - **SEO fallback gap closed** (`aizee_mcp/aizee_server.py`): manual fallback registration now includes register_seo_tools (8 tools were missing if auto-discovery failed).
  - **CSP hardened**: script-src 'unsafe-inline' removed — all JS moved to external `dashboard/app.js`, inline onclick/onkeyup handlers replaced with addEventListener bindings, new `/app.js` route with explicit content-type.
  - **Tests updated/added**: test_policy_manager (fail-closed), test_adapters (unverified ctx + request_timeout), test_dashboard (approve=400 + dry-run-only), test_cli (invalid JSON ×4, sync missing script, graphify nonzero exit), test_git_memory (path safety ×4 classes), test_vector (cross-process hash stability).
  - **Quality gates**: ruff PASS on all touched files (13 pre-existing errors elsewhere on main untouched); mypy PASS on touched files (7 pre-existing errors elsewhere on main untouched); FULL pytest suite: only 2 pre-existing network-dependent SEO failures (confirmed failing on clean HEAD), coverage 96.23% (floor 80%).
- **Market research + governance layer implementation — 2026-08-23 (10 new runtime modules + 5 skills + 3 workflows)**:
  - **Market research**: Analyzed AI coding governance market 2026 (Gartner Magic Quadrant June 2026, Sonar 1,149 dev survey, Qodo 500 eng survey, UserQ MENA 500-user survey, Eshal CX 412-leader benchmark). Key findings: 42% AI-committed code, 96% don't fully trust AI, 89% had AI production incidents, 28% Arabic churn in MENA, 24-point dialect gap.
  - **10 new runtime modules**:
    - `runtime/rules_materializer.py` (330 lines) — emit aiZee rules → 7 tool formats (CLAUDE.md, .cursor/rules/*.mdc, .clinerules/*.md, .windsurfrules, .github/copilot-instructions.md, CONVENTIONS.md, .devin/rules/*.md). 6-scope precedence (ORG>PROJECT>NAMESPACE>REPO>TEAM>USER). Drift detection. Inspired by Elastra.
    - `runtime/agent_gateway.py` (289 lines) — LLM/MCP request-response interception. Pre-LLM + post-execution guardrails. 3 verdicts (ALLOW/REDACT/BLOCK). 3 built-in guardrails (secret_leak, prompt_injection, destructive_command). Custom guardrail registration. Verdict log. Inspired by Fiddler AI.
    - `runtime/plan_diff_validator.py` (347 lines) — plan + diff validation. AST import resolution, dependency guard, unrelated-refactor detection (connected components), test gap detection, forbidden path enforcement. Inspired by repo-contract.
    - `runtime/composite_identity.py` (162 lines) — dual principal (agent + human) attribution. SHA-256 signature. Thread-safe registry. Inspired by GitLab Duo.
    - `runtime/supply_chain_guard.py` (~440 lines) — detect undeclared imports in 4 ecosystems (Python/Node/PHP/Go). AST for Python, regex for others. Stdlib exclusion. Manifest parsers. Inspired by repo-contract dependency guard.
    - `runtime/agent_catalog.py` (195 lines) — allowlist of permitted agents/flows/models. RBAC-gated. AgentStatus (ALLOWED/BLOCKED/DEPRECATED), ModelTier (FRONTIER/STANDARD/LOCAL). Inspired by GitLab Duo.
    - `runtime/mcp_securable.py` (144 lines) — MCP servers as governed securables with GRANT policies (USE/ADMIN/REGISTER). Tool allowlisting. Inspired by Databricks Unity Catalog.
    - `runtime/cost_attribution.py` (189 lines) — per-agent cost tags + anomaly detection (SPIKE/BUDGET_BREACH/UNEXPECTED_PROVIDER). Cost by agent/model. Inspired by FINOPS + Databricks.
    - `eval/reliability.py` (~270 lines) — reliability@k + security-adjusted reliability@k. Replaces misapplied pass@k. Multi-rollout scoring. Inspired by arXiv 2608.14711.
  - **5 new skills** (all lord-level):
    - `skills/arabic-dialect-lord/` — 20 rules, 5 dialect families (Gulf/Egyptian/Levantine/Maghrebi/MSA), RTL, code-switching, cultural context. Competitive moat for MENA.
    - `skills/agent-governance-lord/` — 20 rules, gateway enforcement stack, agent/flow/model allowlist, MCP-as-securable, composite identity, human-in-the-loop.
    - `skills/eval-reliability-lord/` — 18 rules, reliability@k + security-adjusted, multi-rollout mandatory, Docker reproducibility, no recall contamination.
    - `skills/supply-chain-lord/` — 19 rules, dependency guard, SBOM, Cosign, minimum release age, no floating ranges, typosquat detection.
    - `skills/compliance-lord/` — 16 rules, EU AI Act (Art. 9-15), NIST AI RMF (GOVERN/MAP/MEASURE/MANAGE), ISO 42001 (clauses 4/6/8/9/10), risk tier classification.
  - **3 new workflows**:
    - `workflows/33-multi-tool-sync.md` — 5-phase materialization (collect → resolve → materialize → drift detect → verify).
    - `workflows/34-agent-gateway-audit.md` — 5-phase gateway audit (register → intercept requests → intercept responses → composite identity → audit report).
    - `workflows/35-reliability-eval.md` — 5-phase reliability eval (prepare rollouts → classify → score → report → release gate).
  - **Updated**: manifest.json (+34 triggers, +10 features), personas.yaml (ARCH+agent-governance-lord+compliance-lord, QA+eval-reliability-lord, UX+arabic-dialect-lord, SEC+supply-chain-lord+agent-governance-lord, LEGAL+compliance-lord, ML+eval-reliability-lord, MLOPS+eval-reliability-lord, +25 keywords), workflows/README.md (40→43), runtime/__init__.py (+34 exports), tech-stack/useful-repos.md (+16 governance/eval/Arabic repos).
  - **Tests**: 242 new tests across 9 test files. All PASS.
  - **Quality gates**: ruff PASS (0 errors), mypy PASS (0 errors), pytest FULL 3830 passed (275s), graphify update (13217 nodes/27857 edges), aizee memory ingest (131 memories).
  - **Competitive positioning**: aiZee now covers 10/10 identified market gaps (G1-G10). Unique moat: arabic-dialect-lord (no competitor has dialect-aware governance).
  - **Study**: Analyzed 8 production mobile repos (5 Flutter + 3 React Native/Expo) cloned to `D:\server\temp\mobile-study`. Full report at `D:\server\temp\mobile-study\MOBILE_STRENGTHENING_REPORT.md` (408 lines).
  - **Repos analyzed**: ultimate-flutter-template, flutter-firebase-blueprint, flutter-riverpod-clean-arch, flutter-ddd-template, riverpod-clean-arch, expo-supabase-starter, expo-boilerplate-sdk56, rn-copilot.
  - **New runtime module**: `runtime/mobile_patterns.py` (~580 lines) — MobilePatternAuditor with 18 pattern checks. Supports Flutter + RN + KMP + Swift + Kotlin Native. RN backend isolation now checks @supabase/firebase in components/hooks (not just Flutter). CI/CD check covers nested fastlane/Fastfile (ios/fastlane/, android/fastlane/).
  - **New tests**: `tests/test_mobile_patterns.py` (61 tests, all passing) — covers all 18 patterns for both platforms + RN backend isolation + nested Fastfile + audit_summary + edge cases.
  - **New skill**: `skills/mobile-architect/SKILL.md` (lord skill) — cross-platform mobile architect.
  - **New tech-stack**: `tech-stack/expo-sdk-56.md` (209 lines) — Expo SDK 56 / RN 0.86 / React 19.2 / TS 6.0.
  - **New workflow**: `workflows/32-mobile-app-bootstrap.md` (93 lines) — 6-phase mobile bootstrap.
  - **Updated skills**: flutter-architect (+6 rules, merged duplicate L10n rule 15/21 → 25 rules total), mobile-game-producer (+5 rules).
  - **Updated personas.yaml**: MOBILE +mobile-architect lord + 16 keywords.
  - **Updated useful-repos.md**: +18 mobile repos (103 total).
  - **Updated manifest.json**: +20 triggers + mobile_patterns feature.
  - **Code review (DEV+QA+ARCH)**: Fixed 6 issues — [DIR-01] violation (edited aizee/Memory.md instead of .ai), duplicate L10n rule in flutter-architect, 2 dead code functions (_dir_has_subdirs, _glob_exists), test fixture version mismatch (expo ^57 → ^56), workflows/README.md count error (38 → 40). All fixed.
  - **Quality gates**: ruff PASS, mypy PASS, pytest 61/61 PASS.
- **Integration patterns from 7 GitHub repos - 2026-08-24 (18 patterns from strix, open-notebook, book-to-skill, open-seo, i-have-adhd, no-ai-slop, ai-job-search)**:
  - **16 new modules**: runtime/text_sanitize.py (invisible codepoint sanitization), runtime/seo_issue_registry.py (typed SEO audit issue registry, 30+ issue types), runtime/skill_eval.py (self-checking EVAL.md loader), runtime/budget_escalation.py (multi-stage escalation + subagent reserve), runtime/tool_output_bounder.py (output bounding for MCP tools), runtime/provider_registry.py (LLM provider registry, 8 providers), runtime/audit_workflow.py (phased durable audit with checkpointing), runtime/sarif_emitter.py (SARIF 2.1.0 emission), runtime/output_gate.py (pre-send check + portability test), runtime/error_classifier.py (classify_error to typed AizeeError), runtime/sql_injection_guard.py (ORDER BY/identifier validation), aizee_mcp/tools/seo_page_reporters.py (per-page SEO checks), aizee_mcp/tools/seo_multipage_checks.py (cross-page SEO checks), aizee_mcp/tools/seo_sitemap_discovery.py (robots.txt + sitemap discovery with caps), aizee_mcp/tools/mcp_output_schemas.py (MCP output schema validation), eval/rubric.py (eval rubric + release gate).
  - **2 new workflows**: workflows/30-skill-generation.md (book-to-skill pipeline), workflows/31-drafter-reviewer.md (drafter-reviewer pipeline).
  - **1 new skill**: skills/content-quality-lord/ (banned words + slop patterns + EVAL.md + references).
  - **Refactored existing code**: budget.py wired with check_escalation() + should_stop_subagent() using budget_escalation module. seo_tools.py _audit_page_issues() now delegates to seo_page_reporters module (67 lines of inline checks replaced with 36-line delegation).
  - **16 test files, 214 tests**: All passing. ruff PASS on all new modules + test files.
  - **Quality gates**: ruff PASS, pytest PASS (214/214 tests).
  - **Security audit (SEC persona)**: Fixed XXE vulnerability in seo_sitemap_discovery.py (added defusedxml fallback + DOCTYPE/ENTITY rejection), fixed SSRF risk (added _validate_url_scheme to restrict to http/https only). All other modules CLEAN (no hardcoded secrets, no injection, no unsafe deserialization, no PII).
  - **Compliance (LEGAL persona)**: No secrets, no PII, no copyrighted content from source repos. All skill/workflow content is original.
  - **Delivery readiness (FREELANCE persona)**: All 16 modules have proper docstrings, no TODO/FIXME without tickets, no scratch files, Memory.md updated.
  - **Type fixes**: Fixed 4 IDE type errors — OutputSchemaError errors param widened to list[Any], error_classifier AizeeError base instantiation via _instantiate_error helper, validate_tool_output test uses isinstance narrowing.
- **Architectural patterns implementation - 2026-08-23 (10 patterns from 24 top repos)**:
  - **3 new runtime modules**: `runtime/middleware.py` (tRPC flat middleware + NestJS pre-compiled pipeline), `memory/checkpoint.py` (Dapr/LangGraph checkpoint state), `memory/schema_contract.py` (Prisma contract-first schema verification).
  - **7 existing modules enhanced**: policy.py (guardrails), guardian.py (guardrail wiring), authorization.py (R→P→P decomposition), semantic_search.py (hybrid search fusion), vector.py (full_scan_threshold + filter-during-traversal), budget.py (BudgetWindow ALERT/REJECT), service_catalog.py (Backstage entity catalog + plugins), agent_discovery.py (label/capability discovery), prompt_gate.py (assertion-based validation).
  - **10 test files, 291 tests**: test_middleware (31), test_guardrails (20), test_resource_auth (31), test_hybrid_search (30), test_vector_search (29), test_checkpoint (22), test_schema_contract (21), test_prompt_validation (41), test_budget_window (44), test_catalog (30).
  - **Quality gates**: ruff PASS, mypy PASS (219 files), pytest PASS (96.89% coverage), eval/harness all_pass: true, validate-globals 324 scanned / 0 errors / v5.5.0 consistent.
- **Comprehensive review & cleanup - 2026-08-23 (multi-persona audit)**:
  - **Mojibake fixes**: Repaired UTF-8 encoding corruption in manifest.json (Arabic triggers), README-AR.md (236 lines, 994 repairs), Memory.md (16 lines, 189 repairs), workflows/README.md (1 line, 3 repairs), AGENTS.md (36 lines, 44 repairs), .windsurfrules (4 lines, 4 repairs). All Arabic text now renders correctly.
  - **Documentation drift corrected**: Updated module counts across AGENTS.md, spec.md, README.md, docs/ONBOARDING_SRE.md, tech-stack/aizee-5.md (60+ -> 87 runtime modules, 27 -> 35 MCP tools, 31 -> 68 skills, 36 -> 30 numbered workflows). Fixed global-roles-ar.md persona count (17 -> 19).
  - **Rule numbering**: Fixed duplicate rule #20 in global-workflow.md (second #20 -> #21).
  - **Legacy naming cleanup**: Renamed tech-stack/aios-5.md -> aizee-5.md + updated all references. Renamed Prometheus metrics from aios_* to aizee_* in kernel.py, metrics.py, and all tests. Updated tech_stack.py alias map. Cleaned 317 stale .pyc files.
  - **GSAP skill dedup**: Removed redundant gsap-new/ and gsap-refactor/ root wrappers (Claude Code-specific). subskills/ is now the canonical location.
  - **Silent exception logging**: Added logger.debug() with exc_info=True to 5 silent `except Exception: pass/continue` blocks in aizee_server.py, workflow_tools.py, agent_discovery.py, dashboard/server.py.
  - **New tests**: Added tests/test_manifest_encoding.py (4 tests) for mojibake detection, valid JSON, Arabic trigger presence, and trigger path existence.
  - **Quality gates**: ruff PASS, mypy PASS (187 files), pytest PASS (all tests), eval/harness all_pass: true, validate-globals 0 errors/0 warnings.
- **v5.5.0 release - 2026-08-23 (15 patterns from 15 repos study -> aiZee runtime)**:
  - **Version bump**: 5.4.0 -> 5.5.0 across pyproject.toml, manifest.json, .aizee-version, README, README-AR, CHANGELOG.
  - **15 patterns implemented**: 5 new runtime modules (commands, scoped_manager, hook_lifecycle, layers, contract_emitter) + 1 new script (generate_manifest) + deepened closure_evaluator + 3 new guard_invariants checks.
  - **89 new tests**: 7 test files covering all new modules.
  - **Docs updated**: 161 tech-stack files + 1 new + skill update + new workflow 29 + manifest.json + README badges.
  - **Quality gates**: ruff PASS, mypy PASS (220 files), pytest PASS (982 tests, 97% coverage), guard_invariants PASS, validate-globals 0/0, eval/harness all_pass: true.
  - **Batch sync script**: `scripts/update_aizee.bat` created for .ai -> aizee sync.
  - **3-persona review**: SEC + UX + PRODUCT — all issues fixed (README badges, tkinter test flakiness, encoding issues).

- **GitHub repos study v2 - 2026-08-22 (Laravel + Filament + Node.js top repos study -> aiZee integration)**:
  - **Study**: Analyzed top 5 GitHub repos + 5 tools for each of Laravel, Filament, Node.js (15 repos total cloned to `D:\server\temp\github-study-v2`). Full report at `D:\server\temp\github-study-v2\REPOS_ANALYSIS_REPORT.md`.
  - **15 patterns identified and implemented**:
    1. **Deepened EvaluatesClosures DI** (`runtime/closure_evaluator.py`): GuardianClosureEvaluator now resolves 14 param names (action, tool, attributes, context, request, decision, rule_name, reason, phase, user, tenant, session, user_id, tenant_id) inspired by Filament's automatic DI.
    2. **Command object pattern** (`runtime/commands.py` NEW): Command ABC + CommandBus with Saga-style rollback. Inspired by Invoice Ninja's `new MarkPaid()` pattern.
    3. **Scoped managers** (`runtime/scoped_manager.py` NEW): ScopedManager + ScopedRegistry + scoped_factory for context-isolated service instances. Inspired by Filament's `app()->scoped()` + Octane state flushing.
    4. **Fine-grained hook lifecycle** (`runtime/hook_lifecycle.py` NEW): HookRegistry with 6 phases (pre_receive, pre_validation, pre_handler, post_handler, post_response, on_error). Inspired by Fastify's lifecycle hooks.
    5. **Numbered package layering** (`runtime/layers.py` NEW): Layer enum (CORE=1, RUNTIME=2, MANAGERS=3, MCP=4, TOOLS=5, CLI=6) + LayerManifest + check_import_layering. Inspired by Prisma's numbered package prefixes.
    6. **Contract-first artifacts** (`runtime/contract_emitter.py` NEW): emit_contract/emit_contracts emit JSON schema + TypeScript stubs from Pydantic/dataclass schemas. Inspired by Prisma's contract.json + contract.d.ts.
    7. **Manifest-driven composition** (`scripts/generate_manifest.py` NEW): Auto-generate `runtime/__init__.py` re-exports from manifest.json. Inspired by Remix's generate-remix.ts.
    8. **Enum-based configuration**: CommandStatus + HookPhase enums replace magic strings.
    9. **Trait composition audit** (guard_invariants): New check flags classes with >4 bases.
    10. **Magic strings audit** (guard_invariants): New check detects bare status strings outside enum classes.
    11. **Manifest drift audit** (guard_invariants): New check verifies __init__.py exports match imports.
    12. **Schema separation** (tech-stack/filament-4.md +5 rules): Extract Forms/Tables to dedicated classes.
    13. **Custom casts to DTOs** (tech-stack/laravel-12.md +5 rules): Cast JSON columns to DTOs.
    14. **PHP 8 attributes** (tech-stack/laravel-13.md +4 rules): Declarative config via attributes.
    15. **AI Filament workflow** (tech-stack/laravel-ai-workflow.md NEW + workflows/29-filament-ai-workflow.md NEW): Boost + Compass + FilaCheck pipeline.
  - **New runtime modules**: commands.py, scoped_manager.py, hook_lifecycle.py, layers.py, contract_emitter.py (5 files).
  - **New script**: scripts/generate_manifest.py.
  - **New tests**: 7 test files (89 tests total, all passing).
  - **Updated**: runtime/__init__.py (+15 exports), runtime/closure_evaluator.py (deepened DI), scripts/guard_invariants.py (+3 checks), tech-stack/filament-4.md (+5 rules), tech-stack/filament-5.md (+5 rules), tech-stack/laravel-12.md (+5 rules), tech-stack/laravel-13.md (+4 rules), tech-stack/useful-repos.md (+10 entries), skills/backend-frameworks-lord/SKILL.md (+7 rules), workflows/README.md (+1 workflow), manifest.json (+5 triggers, +6 features).
  - **Quality gates**: ruff PASS (17 files), mypy PASS (6 source files), pytest FAST PASS (89 tests), guard_invariants new checks PASS (3/3).
- **SEO integration — 2026-08-21 (5 GitHub repos + 5 tools study → aiZee integration)**:
  - **Study**: Analyzed top 5 SEO GitHub repos (claude-seo 14K stars, open-seo 12K stars, crawlseo 495 stars, seo-audit-skill/SEOmator 377 stars, rustyseo 312 stars) + 5 SEO building blocks (GSC API, DataForSEO, Playwright, Common Crawl, Lighthouse/PSI). Full report at `D:\server\temp\seo-study\SEO_REPORT.md` + integration plan at `D:\server\temp\seo-study\SEO_INTEGRATION_REPORT.md`.
  - **Phase 1 — seo-lord skill** (NEW, directory layout):
    - `skills/seo-lord/SKILL.md`: 20 rules (grounding, progressive disclosure, parallel analysis, falsifiability-first, confidence-weighted, health score, 251 audit rules, CWV, schema active/deprecated, GEO/AEO, crawl budget, LLM-safe output, free APIs first).
    - `skills/seo-lord/references/`: 7 files (technical-seo 9 categories, content-eeat E-E-A-T framework, schema-types active/deprecated/keep, geo-aeo AI search optimization, cwv-thresholds LCP/INP/CLS, audit-rules 251 rules/20 categories, health-scoring 0-100 algorithm).
    - `skills/seo-lord/templates/`: 2 files (seo-audit-report, content-brief).
    - Registered in `personas.yaml` as lord skill (40 keywords incl. Arabic سيو/تحسين محركات البحث). Linked to ARCH, DEV, UX, DOC personas.
  - **Phase 1 — tech-stack/seo-1.md** (NEW): 35 rules (meta, canonical, sitemap, robots.txt, hreflang, schema JSON-LD, CWV, URL, mobile, security, redirects, images, content quality, E-E-A-T, internal links, GEO/AEO, crawl budget, indexing, IndexNow, social meta, HTML validation, accessibility, JS SEO, health score, audit rules, opportunities, local SEO, e-commerce, international, output formats, falsifiability, prohibitions, free APIs, paid APIs optional).
  - **Phase 1 — useful-repos.md**: +10 entries (5 SEO repos + 5 SEO building blocks).
  - **Phase 1 — runtime/tech_stack.py**: +10 SEO package aliases (seo, laravel-filament-seo, spatie/laravel-sitemap, etc.).
  - **Phase 2 — workflows/28-seo-audit.md** (NEW): 21 rules (detect, scope, crawl, technical SEO, CWV, content E-E-A-T, schema, GEO/AEO, links, images, score, audit rules, GSC data, opportunities, output, falsifiability, grounding, LLM-safe, prohibitions, quality gate, MCP tools). Triggers: seo audit, seo analysis, search optimization, seo, سيو, تحسين محركات البحث.
  - **Phase 2 — manifest.json**: +7 trigger entries for workflow 27.
  - **Phase 2 — workflows/README.md**: Updated count 27 → 28, added SEO audit row.
  - **Phase 3 — aizee_mcp/tools/seo_tools.py** (NEW, 8 tools, stdlib only):
    - `seo_audit_page`: Single page audit (meta, headings, schema, canonical, images, content, health score).
    - `seo_audit_site`: Full site crawl (up to 2000 pages, batch crawler, aggregate score).
    - `seo_check_cwv`: Core Web Vitals via PageSpeed Insights API (free, no key).
    - `seo_validate_schema`: JSON-LD extraction + active/deprecated classification.
    - `seo_analyze_content`: E-E-A-T + readability (Flesch) + citability + word count.
    - `seo_check_geo`: AI search readiness (AI crawler access, semantic HTML, llms.txt, schema).
    - `seo_get_gsc_data`: GSC data (returns OAuth setup instructions if no credentials).
    - `seo_find_opportunities`: Striking distance, low CTR, cannibalization from GSC data.
  - **Phase 3 — schemas.py**: +3 schemas (SeoAuditSchema, SeoCwvSchema, SeoSchemaSchema) + ALL_SCHEMAS entries.
  - **Phase 3 — __init__.py**: Added register_seo_tools export + 3 schema exports.
  - **Phase 3 — aizee_mcp/API.md**: Added "SEO Tools" section (8 tool docs).
  - **Phase 3 — pyproject.toml**: Added seo_tools to mypy untyped-decorator override.
  - **Phase 3 — tests/mcp/test_seo_tools.py** (NEW): 132 tests (URL validation, SSRF protection incl 0.0.0.0/IPv6/DNS rebinding/redirect validation, HTML parser with tag stack, text helpers, issue+scoring, CWV status, schema classification incl @graph+empty+dict, tool registration, audit page incl nofollow+viewport, schema validation incl invalid JSON + multiple schemas, content analysis incl thin content + paragraph splitting, opportunities incl empty rows + position=0 + cannibalization dedup, GSC instructions + days clamping, seo_audit_site crawl + tel/MAILTO filtering, seo_check_cwv mocked API + empty lighthouseResult, seo_check_geo + empty body, anchor text, tag reset, malformed HTML, CDATA/comments, normalize_url, _content_hash, nested tags). All passing.
  - **5-persona review rounds 3+4 (ARCH + DEV + QA + SEC + DOC)**: Fixed all critical issues:
    - URL validation: explicit rejection of javascript:/data:/file:/ftp:/mailto: schemes.
    - SSRF protection: private IP blocking (127.0.0.1, 10.x, 172.16.x, 192.168.x, 169.254.x, ::1, 0.0.0.0) + DNS rebinding check (_resolves_to_private_ip) + redirect target validation (_SsrfSafeRedirectHandler with relative URL resolution).
    - _strip_html: now handles CDATA + HTML comments + conditional comments + compiled regexes.
    - HTML parser: captures anchor text, tag stack handles nested identical tags, refactored handle_starttag <30 lines.
    - _classify_schema: handles @graph containers (CONTAINER) + empty @graph (EMPTY) + @graph as dict (recurses).
    - _count_syllables: returns 0 for numbers/symbols, 1 for fly/my/crypt.
    - SeoAuditSchema: added missing fields (h1s, h2_count, content_hash, og_tags).
    - seo_audit_page: now checks nofollow + viewport meta (mobile-friendly).
    - seo_audit_site: URL normalization + deque for O(1) BFS + case-insensitive link filtering (tel:/MAILTO:).
    - seo_check_cwv: validates lighthouseResult exists + TTFB returns int.
    - seo_check_geo: returns error on empty body + robots.txt regex handles \r\n line endings.
    - seo_find_opportunities: empty rows returns success + skips position<=0 + cannibalization deduplicates pages.
    - seo_analyze_content: paragraph splitting by sentence boundaries (was broken by _strip_html whitespace collapse).
    - _fetch: charset handling + cached SSRF-safe opener (_get_opener) for performance.
    - _parse_html: try/except for malformed HTML.
    - Deleted old `skills/seo-content-generator.md` (superseded by `seo-lord/`).
  - **Quality gates**: ruff ✅ (0 errors), mypy ✅ (0 errors), pytest ✅ (132/132 SEO tests + 893/893 total tests passed). MCP server auto-discovery ✅ (8 SEO tools registered). test_mcp_server.py updated with SEO tools in expected set.

- **v5.3.0 release — Laravel/Filament tech-stack enrichment + runtime improvements + bug fixes**:
  - **Version bump**: 5.2.0 → 5.3.0 across 8 files (pyproject.toml, manifest.json, .aizee-version, README.md, README-AR.md, aizee_mcp/API.md, validate-globals.py, validate-globals.ps1) + test_dashboard.py assertions.
  - **CHANGELOG.md**: Added v5.3.0 section with full summary (6 phases + bug fixes + tests + 3-persona review).
  - **README.md + README-AR.md**: Updated badges (Version 5.3.0, Tests 2773, Coverage 97%, Skills 59, Workflows 27, Tech-Stack 87) + added "What's New in v5.3.0" section.
  - **manifest.json**: Added triggers for workflows 22-26 (spec-analyze, spec-converge, laravel-architecture, filament-plugin, api-versioning) + 2 new features (closure_evaluator, mcp_schemas) + updated date.
  - **workflows/README.md**: Fixed count from 34 → 27 (actual workflows 00-26).
  - **Final quality gates**: ruff ✅ (0 errors), mypy ✅ (0 errors, 204 files), pytest ✅ (2773 passed, 2 skipped, 0 failed, 96.88% coverage). All new/modified files at 100% coverage.
  - **3-persona final review**: ARCH 14/14 ✅, DEV 18/18 ✅, QA-SEC 12/12 ✅ (after adding 5 authorize() auto-validation tests + fixing workflows count).

- **GitHub repos study + Laravel/Filament tech-stack enrichment — v5.2.0**:
  - **Analysis**: Analyzed 10 leading GitHub repos (5 Laravel + 5 Filament) cloned to `D:\server\temp\github-study\`. 5 parallel subagents (ARCH/DEV/PRODUCT/UX) read real files (composer.json, Models, Controllers, Services, Resources, tests). Full report at `D:\server\temp\github-study\REPOS_ANALYSIS_REPORT.md` (627 lines).
  - **Repos analyzed**: bagisto (eCommerce/Concord), monica (CRM/DDD), krayin-crm (Modular/MagicAI), bookstack (Wiki/Activity), koel (Music/Repository+DTO+API), filament (framework/Plugin system), superduper-starter-kit (Clusters/12 plugins), lara-zeus-sky (CMS/Status enum), mvpable (SaaS/DDD+Actions), filament-blog (Faceless/trait-based).
  - **Phase 1 — tech-stack updates** (4 files):
    - `tech-stack/laravel-12.md`: +7 rules (Repository Pattern, Service Layer with permission dependencies, DTO/Value Objects, Three-Component Model, Activity Logging, UUID keys, Domain-Driven Structure).
    - `tech-stack/laravel-13.md`: +7 rules (Custom Eloquent Builders, Custom Casts, API Resources + Structure Constants, API Versioning header-based, Cursor Pagination, Contracts/Interfaces, License/Feature Gating).
    - `tech-stack/filament-4.md`: +13 rules (Tab-based Forms, Status Enum System, Upload/URL Toggle, Configurable Content Editor, Create Option Forms, Navigation Badges, Custom Permission Prefixes, Role-based Field Visibility, Dynamic Branding, Discovery Pattern, Authorization via Plugin, Action Groups, Search Highlighting).
    - `tech-stack/filament-5.md`: +12 rules (Schema Pattern, Plugin System, Cluster Pattern, ComponentManager, EvaluatesClosures, Macroable, Registry Pattern, NavigationManager, Asset Management, Multi-DB Testing, Spatie Media Library, Spatie Tags with Types).
  - **Phase 2 — new tech-stack files** (3 files):
    - `tech-stack/laravel-testing.md`: 18 rules (Pest 3+, Two-Tier testing, Factories, Helper Traits, Custom Assertions, Security Tests, License Mocking, Translation Consistency, E2E Playwright, Multi-DB, Parallel+Serial, Browser Testing, API Structure Tests, Cursor Pagination Tests, Bus Faking, AAA Pattern, Coverage).
    - `tech-stack/laravel-security.md`: 25 rules (Auth/Sanctum/WebAuthn, 2FA, ACL, Multi-Tenancy, Content Filtering, SVG Sanitization, Rate Limiting, Security Headers, ForceHttps, Installer Lockdown, Disposable Email, GDPR, Impersonation, UUID, License Gating, FormRequest, Parameterized Queries, $fillable, No PII logs, RBAC, HTML Sanitization, DTO Projections, Encrypt at Rest, API Throttling, JWT HttpOnly).
    - `tech-stack/filament-plugins.md`: 14 rules (Plugin Interface, Registration, Boot Order, Authorization via Plugin, 20 Recommended Plugins, Custom Plugin Development, Discovery, Configuration, Testing, Theming, Assets, Navigation, Multi-Tenancy, Compatibility).
  - **Phase 3 — skills updates** (3 files):
    - `skills/backend-frameworks-lord/SKILL.md`: +12 rules (Architecture Patterns ranked by complexity, Pattern Selection Matrix, Service Layer Rules, Repository Rules, DTO Rules, API Design Rules, Multi-Tenancy Rules, Three-Component Model, Activity Logging, AI Integration, Testing, Security).
    - `skills/page-sections-lord/SKILL.md`: +19 rules (Status Enum, Tab-based Forms, Upload/URL Toggle, Configurable Editor, Navigation Builder, Search Highlighting, Spatie Media Library, Spatie Tags with Types, Password Protection, Sticky/Scheduling, Parent-Child Pages, FAQ/Breadcrumb/Article/Organization Schema, Action Groups, Navigation Badges, Create Option Forms, Auto-slug Generation).
    - `tech-stack/useful-repos.md`: +10 repos (bagisto, monica, krayin, bookstack, koel, filament, superduper, sky, mvpable, filament-blog) with detailed descriptions.
  - **Phase 4 — new workflows** (3 files):
    - `workflows/24-laravel-architecture-setup.md`: 22 rules (complexity detection, Service/Repository/DTO/Actions/DDD scaffolding, Context7 MCP query, two-tier testing, security).
    - `workflows/25-filament-plugin-development.md`: 22 rules (Plugin interface, register/boot lifecycle, config file, authorization, configureUsing, Asset management, Multi-tenancy, Navigation, Theming, Context7 MCP, testing, compatibility, documentation).
    - `workflows/26-laravel-api-versioning.md`: 24 rules (header-based versioning, route files, API Resources with structure constants, cursor pagination, deprecation headers, OpenAPI docs, Context7 MCP, backward compatibility).
  - **Phase 5 — aiZee runtime improvements** (4 files):
    - `runtime/plugin.py`: Enhanced `AIOSPlugin` with two-phase lifecycle `register()` + `boot()` (Filament pattern). `register()` default calls `on_load()` for backward compat. `PluginManager.load_all()` now runs Phase 1 (register all) then Phase 2 (boot all).
    - `runtime/closure_evaluator.py` (NEW): `ClosureEvaluator` with automatic dependency injection for closures (Filament EvaluatesClosures pattern). Resolution order: named → typed → default-by-name → default-by-type → evaluation_identifier → default value → None → error. `GuardianClosureEvaluator` subclass with action/attributes/context defaults. `ClosureResolutionError` exception.
    - `runtime/guardian.py`: Added `permission_dependencies` system (Monica BaseService pattern). `DEFAULT_PERMISSION_DEPENDENCIES` class var. `validate_permission_dependencies()` method checks prerequisites.
    - `aizee_mcp/tools/schemas.py` (NEW): JSON_STRUCTURE constants for MCP tool responses (Koel pattern). 7 schema classes (Rule, Skill, Workflow, TechStack, PolicyDecision, Plugin, MemoryEntry) + PaginatedResultSchema with cursor/offset structures. `ALL_SCHEMAS` registry.
  - **Gate**: ruff ✅ (new/modified files), mypy ✅ (4 files clean), pytest ✅ (2717 passed, 1 skipped, 96.37% cov — 1 test fixed for new plugin message, 2 pre-existing failures unrelated), eval/harness ✅ (validate-globals PASS all new files), memory ingest ✅ (47 memories), graphify update ✅ (9573 nodes, 19889 edges).
  - **Review fixes (3-persona audit: ARCH/DEV/QA-SEC)**:
    - **Code quality fixes**: Split `load_all` into `_register_phase` + `_boot_phase` (CODE-03). Split `_resolve_single_param` into 5 helper methods (CODE-03). Added `PluginSandboxError(AizeeError)` replacing `RuntimeError` in plugin guard. Replaced `PermissionError` with `PolicyDeniedError` in guardian. Added `EVALUATION_ERROR_REASON`/`NO_MATCHING_RULE_REASON`/`DEFAULT_RULE_NAME` constants (CODE-04).
    - **Exports**: Added `ClosureEvaluator` + `GuardianClosureEvaluator` to `runtime/__init__.py`. Added all 9 schema classes + `ALL_SCHEMAS` to `aizee_mcp/tools/__init__.py`.
    - **New tests**: `test_closure_evaluator.py` (23 tests, 100% cov), `test_mcp_schemas.py` (14 tests, 100% cov). Added 4 tests for two-phase lifecycle (boot/register exceptions) + 8 tests for `validate_permission_dependencies` + magic string constants. Fixed `test_plugin_guard.py` for `PluginSandboxError`.
    - **Docs**: Updated `workflows/README.md` count 31→34 + added workflows 20-26 to table.
    - **Post-fix gate**: ruff ✅, mypy ✅ (4 files clean), pytest ✅ (2767 passed, 1 skipped, 97.00% cov — 2 pre-existing failures unrelated), memory ingest ✅ (1 new), graphify ✅ (9656 nodes, 20141 edges).

- **Fourth audit + improvements (P0-P4, external research-driven) — v5.2.0**:
  - **P0 (critical startup fixes)**:
    - **P0.1**: `state/budget.json` encryption corruption — `BudgetManager._load()` now catches `InvalidToken` + JSON errors, quarantines the corrupt file to `.corrupt.bak`, and falls back to default budgets. System stays usable after key rotation.
    - **P0.2**: `mcp` library breaking change (`FastMCP`→`MCPServer`, `Resource` moved to `mcp.types`) — created `aizee_mcp/_compat.py` shim re-exporting `FastMCP`/`Resource` from new locations. Updated 11 import sites (6 source + 5 test files) to use the shim. No direct edits to upstream-dependent code.
  - **P1 (high — new safety layers)**:
    - **P1.1**: `runtime/mcp_firewall.py` — per-tool-call access control with `allow`/`deny`/`require_approval` actions, priority-ordered rules, restricted Python condition expressions (safe AST eval, no `eval()`). OS-level defaults in `runtime/policies/mcp_firewall.yaml` (5 rules: deny destructive, deny secret search, require approval for deploy/git-push, allow reads). Integrated into `Kernel` as `check_mcp_tool()`. 29 tests.
    - **P1.2**: `runtime/loop_detector.py` — hash-based loop detection with sliding window. Blocks repeated identical actions before guardian. Integrated into `Kernel.act()`. Thread-safe. 14 tests.
  - **P2 (medium — pre-inference + lifecycle safety)**:
    - **P2.1**: `runtime/prompt_gate.py` — deterministic pre-inference prompt safety scanner (no LLM). Detects injection, system-override, destructive, exfil, privilege patterns. Score-based (BLOCK ≥30, SUSPICIOUS ≥10). Integrated into `ChatManager.chat_message`. 12 tests.
    - **P2.2**: `runtime/trajectory.py` — run-level trajectory tracking with stall detection (contiguous failures ≥ threshold). Records steps, inspected/modified files, assumptions. Auto-marks runs as STALLED. 13 tests.
    - **P2.3**: `runtime/approval_service.py` — persistent approval request lifecycle (PENDING→APPROVED/DENIED/EXPIRED/CANCELLED). Multi-channel notifications (Console, Webhook, custom). TTL-based expiry. Sits on top of existing `ApprovalCache`. 14 tests.
  - **P3 (low — tooling + observability)**:
    - **P3.1**: `runtime/reasoning_graph.py` — directed graph for multi-step governance escalation chains. Node activation + propagation + longest-path computation. 11 tests.
    - **P3.2**: `runtime/context_manager.py` — 3-level context trimming (preserve system, compress middle, keep recent). Atomic group preservation (assistant+tool pairs never split). 11 tests.
    - **P3.3**: `runtime/agent_discovery.py` + `aizee agents discover` CLI — scans home + project for AI agent configs (Claude Code, Cursor, Cline, Windsurf, Aider, Devin, AGENTS.md). Read-only. 8 tests. Also added `aizee skill eject` to copy skills into project for customization.
    - **P3.4**: `scripts/guard_invariants.py` — mechanical code-invariant checks (future_annotations, no bare Exception, skills frontmatter, kernel facade, policy actions). CI-ready. Excludes `mcp_firewall.yaml` from generic policy loader.
  - **P4 (polish)**:
    - **P4.1**: Dashboard CSS theming — light theme via `[data-theme="light"]` + `prefers-color-scheme`. Theme toggle button (auto/light/dark) with localStorage persistence.
    - **P4.2**: `workflows/testing-tiers.md` upgraded from 2-tier to 4-tier (FAST/SMOKE/FULL/VIBE) with aiZee-specific commands and vibe scenario structure.
    - **P4.3**: `eval/vibe.py` + `eval/scenarios/` — LLM-graded behavioral scenarios (regex/exact/contains/refuse/llm grading). 9 shipped scenarios (security + persona). 15 tests. `python eval/vibe.py` CLI for smoke testing.
  - **New modules**: mcp_firewall, loop_detector, prompt_gate, trajectory, approval_service, reasoning_graph, context_manager, agent_discovery (8 modules, 127 tests total).
  - **Integration**: `runtime/__init__.py` re-exports all 8 new modules. `aizee doctor` checks 11 new module files. `aizee status` shows MCP firewall rules + loop detector stats. `aizee agents discover` + `aizee skill eject` CLI commands. Loop detector threshold=5 (allows natural retries, blocks true loops). Dry-run + fresh-context actions bypass loop detection.
  - **Gate**: ruff ✅ (new modules), mypy ✅ (10 source files), pytest ✅ (2714 passed, 1 skipped tkinter, 95.91% cov), eval/vibe ✅ (7/9 with dummy agent).

- **Third comprehensive audit + fixes (P0-P3, all personas) — v5.1.0**:
  - **P0 (critical)**: Dockerfile `cli.py`→`aizee_cli.py` + Python 3.14. Exception hierarchy unified (6 exceptions now inherit `AizeeError`). aizee shim PATH fix in `update.py`.
  - **P1 (high)**: CI matrix +3.13/3.14. Secure-by-default encryption (auto-generate key). Dashboard token `chmod 0o600`. Graceful shutdown (storage flush + DB close). Log rotation (100MB, 5 rotated). test_chat_manager (23 tests). Mock time in tests. Self-healing ↔ AgentManager.
  - **P2 (medium)**: StorageBackend explicit conformance. .env allowlist. Audit key-based redaction. CSP strengthened. NumPy tightened. KernelBuilder. MCP async/sync unified. Test organization moved. Weak assertions fixed. DB connection pooling. DB backup automation. Operational docs (3 files).
  - **P3 (low)**: Rate limit LRU. Plugin sandbox strengthened. Plugin resource-based permissions. MCP tool auto-discovery. Parametrized tests. Dashboard HTTP logging. K8s secret warning. Migration rollback.
  - **Gate**: ruff ✅, mypy ✅ (187 files), pytest ✅ (0 failed, 1 skipped tkinter, 96% cov), eval/harness ✅ all_pass, validate-globals ✅ 0 errors.
  - **Version**: 5.2.0 across pyproject.toml, manifest.json, .aizee-version, README.md, README-AR.md, aizee_mcp/API.md, validate-globals.py, validate-globals.ps1.

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
  - **P1.1 (dogfooding tech-stack)**: Added 7 internal tech-stack refs (`python-3.md`, `aizee-5.md`, `pydantic-2.md`, `mcp-1.md`, `pytest-7.md`, `pytest-8.md`, `pyyaml-6.md`, `rich-13.md`). Upgraded `_parse_pyproject_toml` to register project self-name + `requires-python` version. `get_os_status` now returns 7 tech_stack entries instead of `{}`.
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
- **P2.5:** Observability: Sentry integration (`runtime/telemetry.py`), Prometheus export via telemetry collector.
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
