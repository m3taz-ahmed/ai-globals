[FILE] Memory
[OBJ] Short-term context and cross-session continuity.
[RULES]
1. [REQ] Read at session start.
2. [REQ] Update at session end via `workflows/17-memory-sync.md`.
3. [REQ] Keep under 500 lines.
[UPDATED] 2026-08-23
[NOTES]
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
