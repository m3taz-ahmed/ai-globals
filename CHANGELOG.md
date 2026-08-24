# Changelog

## [5.7.1] - 2026-08-24 (Comprehensive Review: 17 Fixes Across 125 Files)

### Critical Fixes (3)
- **k8s NetworkPolicy egress** (`deploy/k8s/deployment.yaml`): `to: []` blocked ALL outbound traffic. Fixed to allow HTTPS egress to any destination.
- **schema_contract missing memory_decay** (`memory/schema_contract.py`): `memory_decay` table created in `store.py` but missing from `default_memory_contract()` → schema drift warnings on every init. Added table + index to contract.
- **mcp_firewall.yaml default_action silently ignored** (`runtime/policies/mcp_firewall.yaml`): GATE-B3 restriction caused `default_action: allow` to be silently dropped → MCP tools became `ask` instead of `allow`. Fixed by removing `default_action` and adding catch-all allow rule with priority 0. Also fixed YAML parsing error (unquoted colon in description).

### High Priority Fixes (3)
- **Missing runtime exports** (`runtime/__init__.py`): 12 new module exports missing (ConfidenceGate, LearningLoop, SkillRouter, Bounder, Witness, LazyImport, ReflexionLog, OutputEnvelope, CostProvider, etc.). Added all exports + `__all__` entries.
- **Probity normalization inconsistency** (`runtime/probity.py`): `EnforceFilenameCasing` and `EnforceTdd` checked `("write", "edit")` directly instead of using `normalize_action_type()`. Fixed to use consistent normalization.
- **Constitution regex too narrow** (`runtime/spec/engine.py`): `r"MUST\s+(.+?)(?:\.|$)"` missed principles ending with `!`, `?`, `;`, `:`, or newlines. Fixed to `r"MUST\s+(.+?)(?:[.!?;:]|\n|$)"`.

### Medium Priority Fixes (5)
- **delete_by_source_batch length validation** (`memory/store.py`): No length limit on source strings. Added 1000-char max validation.
- **ConfidenceGate weight validation** (`runtime/confidence_gate.py`): No validation that weights are in [0.0, 1.0]. Added validation with ValueError on out-of-range.
- **LazyImport error handling** (`runtime/quality.py`): Malformed import paths raised cryptic errors. Added path validation + try/except with clear error messages.
- **Priority parsing error handling** (`runtime/policy.py`): `int(r.get("priority", 0))` crashed on non-numeric strings. Added `_safe_priority()` helper with try/except + warning.
- **FTS5 sanitization enhanced** (`memory/store.py`): Parentheses and hyphens not stripped from FTS5 queries. Added to sanitization regex.

### Policy Files Cleanup (6 files)
- Removed `default_action` from 5 non-default policy files (agentic-owasp.yaml, consequence-tiers.yaml, mcp_firewall.yaml, examples/api-rate-limits.yaml, examples/data-exfiltration.yaml, examples/time-based-access.yaml). Only default.yaml now sets default_action per GATE-B3.

### New Tests (17)
- Weight validation tests (5) in test_confidence_gate.py
- LazyImport error handling tests (3) in test_quality.py
- Priority parsing tests (6) in test_policy.py
- delete_by_source_batch validation tests (4) in test_memory_upgrades.py

### Quality Gates
- ruff: PASS (repo-wide, 0 errors)
- mypy: PASS (240 source files, 0 errors)
- pytest: Full suite green (exit code 0, 1 skip for tkinter)

## [5.7.0] — 2026-08-24 (Implementation Plan Remediation: 8 Workstreams, 40+ Items)

### WS-C: Dead Code Removal
- Removed 26 dead runtime modules + their test files
- Updated manifest.json, README.md, README-AR.md, AGENTS.md, spec.md, tech-stack/aizee-5.md
- Runtime module count: 105 → 81

### WS-B: Gate-Contract Repairs
- **GATE-B1**: Structured denial for probity violations (catch `GuardrailViolationError` → structured dict)
- **GATE-B2**: `normalize_action_type()` maps Bash/Shell/Command → exec, Apply/Patch → write
- **GATE-B3**: Audit (rule names in denial), `_MISSING` sentinel prevents None==None escalation, policy `priority` field + sorting, `default_action` writable only by default.yaml
- **GATE-B4**: Deprecated bypass paths `register_action_pipeline()` / `_get_compiled_pipeline()`

### WS-A: Security Hardening
- **SEC-W1**: Dashboard loopback enforcement (`AGENT_OS_HOST`, `_is_loopback_host()`)
- **SEC-W2**: K8s deploy manifests (NetworkPolicy ingress/egress restrictions, README)
- **SEC-W3**: Dashboard robustness (Content-Length parsing, `?limit=` on audit/tracing, SSE headers + max duration)

### WS-D: Eval Overhaul
- **EVAL-W0**: `GateVerdict` unified dataclass + `to_gate_verdict()` adapters (prompt_gate, mcp_firewall, agent_gateway)
- **EVAL-W1**: `eval/pipeline.py` — real kernel.act() pipeline (no vibe checks)
- **EVAL-W2**: 10 executable assertion kinds (eq, contains, not_contains, regex, key_exists, ok_true, ok_false, decision_is, gate_is, custom)
- **EVAL-W3**: `AnchoredDimension` rubric anchored to executable assertions
- **EVAL-W5**: `eval/redteam.py` — red-team runner + SARIF 2.1.0 reporter
- **EVAL-W6**: Per-gate + per-policy breakdown in pipeline results

### WS-E: SDD Enforcement
- **W1**: Task verification (evidence + `verified` flag blocks phase advance)
- **W2**: Constitution enforcement (MUST principles checked against requirements)
- **W3**: State transition history (audit trail in `state_history`)
- **W4**: Drift v2 (file modifications + unapplied deltas + phase regressions)
- **W5**: Paginated spec listing (`list_specs_paginated`)
- **W6**: Delta hardening (validate references, duplicates, empty descriptions)

### WS-F: Memory Upgrades
- **W1**: Deterministic IDs (content hash → stable `mem_XXXX` IDs)
- **W2**: Deduplication (same content → same ID → no-op on re-add)
- **W3**: Fact extraction (heuristic verb-based sentence extraction)
- **W4**: Temporal search (`search_temporal` by valid_from range)
- **W5**: Decay persistence (`memory_decay` table, `record_access`/`apply_decay`/`get_decay_score`)
- **W6**: Search hardening (`search_safe` with length/null-byte/SQL-keyword sanitization)

### WS-H: Confidence Gating
- `runtime/confidence_gate.py` — `ConfidenceGate` with weighted evidence, `ConfidenceVerdict` (frozen), 4 confidence levels, fail-closed

### WS-G: Learning Loop
- `runtime/learning_loop.py` — LEARN-01 hook bindings (auto-record via POST_RESPONSE + ON_ERROR); LEARN-02 record-consolidate-rank-inject with persistence

### WS-I: Skills/Personas
- `runtime/skill_routing.py` — SKILL-W1 `SkillRouter` routing meta-prompt; SKILL-W2 `PersonaDetectorV2` with confidence + ambiguity detection

### WS-J: Misc Quality
- `runtime/quality.py` — W1 `CostProvider`/`FixedRateCostProvider`; W3 assertion helpers; W5 `OutputEnvelope`; W6 `Bounder`; W7 `Witness`/`WitnessRecorder`; W8 `LazyImport`; W9 `ReflexionLog`

### Quality Gates
- ruff: PASS (repo-wide, 0 errors)
- mypy: PASS (240 source files, 0 errors)
- pytest: Full suite green (1 skip for tkinter display)
- 200+ new tests across 11 new test files

## [5.6.0] — 2026-08-23 (Security Hardening + Quality Gates Zeroed + Docs Sync Automation)

### Critical Security Fixes (3)
- **Policy evaluator privilege-escalation** (`runtime/policy.py`): YAML-style `true`/`false`/`null` literals in conditions were parsed as variable names. `flag == true` matched every action MISSING that flag (`None == None → True`). `reversible == true → allow` auto-approved all write/edit/apply regardless of reversibility. Fixed via `_yaml_literals` mapping + fail-closed TypeError handling. 13 regression tests (`test_policy_evaluator_security.py`).
- **Guardian fail-closed** (`runtime/managers/policy_manager.py`): broken `guardian.authorize` now denies with `guardian_error` + audit log instead of silently allowing.
- **approve-via-GET removed** (`dashboard/server.py`): GET `/api/check` is dry-run only; `?approve=1` returns 400. Closes localhost CSRF privilege escalation.

### Security Hardening (9 more fixes)
- **verify_ssl effective** (`aizee_mcp/adapters.py`): False builds a real unverified SSL context (+ init warning); previously returned None = default verified context.
- **A2A timeouts**: launch/poll pass `request_timeout` (default 30s) + SSL context; socket timeouts mark sessions failed instead of hanging.
- **Stable vector ids** (`memory/vector.py`): non-UUID fallback hashes via blake2b (was salted `hash()` → orphaned vectors after restart).
- **Checkpoint thread-safety** (`memory/checkpoint.py`): RLock around shared SQLite connection.
- **Non-strict output validation hardened** (`aizee_mcp/tools/mcp_output_schemas.py`): dropped `model_construct` bypass; invalid fields dropped then re-validated.
- **git_memory path sanitization** (`memory/git_memory.py`): category/entry_id validated against safe-component regex (blocks traversal).
- **CLI error handling** (`aizee_cli.py`): friendly errors for malformed JSON args; sync/graphify report failures instead of tracebacks/silent success.
- **SEO fallback registration** (`aizee_mcp/aizee_server.py`): manual fallback now registers all 8 SEO tools.
- **Dashboard CSP**: script-src 'unsafe-inline' removed — JS moved to external `dashboard/app.js`, inline handlers replaced with addEventListener.

### Dashboard (Design Decisions)
- **Open-access by default**: tokens removed by default; auth is OPT-IN via `AIZEE_DASHBOARD_TOKEN` env only. Safety preserved by 127.0.0.1 binding + read-only GETs + CSRF custom-header on POSTs.
- **Assets served from code directory**: `/`, `/app.js`, `/index.css`, favicons resolve from server code's own directory (`_asset_dir()`) — never from discovered root. Fixes version-mismatch dead UI. Tests use `_ASSET_DIR_OVERRIDE`.
- **Cache-Control: no-cache** on all responses (prevents stale-shell breakage after upgrades).
- **Direct execution hardened**: `python dashboard/server.py` bootstraps sys.path for any CWD.

### Architecture & Refactor
- **spec_engine.py (876 lines) split** into `runtime/spec/` package: models / engine / scaffold / analysis / templates. `runtime.spec_engine` remains a backward-compatible facade.
- **Persona injection unified**: single `inject_persona_context()` in `runtime/persona.py` replaces 3 duplicated blocks (kernel/workflow_manager/workflow).
- **Read-only classification unified**: `PolicyManager._READ_ONLY_ACTIONS` derives from canonical `READ_ACTIONS` in `runtime/policy.py` (+ ChatMessage).
- **ChatManager implemented**: new `runtime/local_responder.py` answers status/budget/workflow/rules/skills/stack intents from live kernel state (zero tokens, honest offline label) instead of hardcoded "Acknowledged".

### Tooling & Docs
- **`scripts/sync_docs.py`** (new): counts + workflow routing table regenerated from filesystem truth; `--check` wired into CI validate workflow.
- **`CONTRIBUTING.md`** added: two-tier testing, code standards, module/skill/workflow recipes.
- **pytest-timeout** wired (300s, thread method) guarding CI against hung tests.
- **True async tests added**: Guardian invoke/ainvoke decorators + A2A adapter executor path.
- **CI validate.yml**: type-check corrected to `aizee_cli.py` (was nonexistent `cli.py`); docs sync check added.
- **Counts synced**: AGENTS.md/spec.md (105 modules / 73 skills / 36 workflows / 163 stack refs); README/README-AR badges updated.

### Quality Gates → Green
- **mypy: 0 errors** across runtime/memory/aizee_mcp/config/cli/dashboard (268 files) — was 7 pre-existing.
- **ruff: 0 errors** repo-wide — was 13 pre-existing.
- **Full suite green** (~4,050 tests), coverage 96.26% (floor 80%).

### Version Bump
- 5.5.0 → 5.6.0 across: pyproject.toml, .aizee-version, manifest.json, README.md, README-AR.md, tech-stack/aizee-5.md, aizee_mcp/API.md, scripts/validate-globals.{py,ps1}, tests/dashboard/test_dashboard.py.

## [Previous] — Dashboard: Assets Served From Code Directory (Version-Coherence Fix)

- **User-reported dead UI** ("Connecting..." stuck, side menu unresponsive in every browser): running the new server while `AIZEE_ROOT` pointed at another install served OLD inline-script markup under the NEW strict CSP, silently blocking all JS. Verified via headless Chromium that matching assets work.
- **Fix**: `/`, `/app.js`, `/index.css`, favicons and logo now resolve from the server code's own directory (`_asset_dir()`), never from a discovered root — UI and server are always the same version. Tests use `_ASSET_DIR_OVERRIDE`.
- Added `Cache-Control: no-cache` to every response so upgraded shells are always re-fetched.

## [Previous] — Dashboard: Open-Access by Default (Tokens Now Opt-In)

- **Design decision**: dashboard authentication is no longer automatic. `state/dashboard.token` files and auto-generation are removed entirely; the only auth source is the `AIZEE_DASHBOARD_TOKEN` env var. Unset (default) = open APIs.
- Safety without a token is preserved by: 127.0.0.1 default binding, read-only/dry-run GETs (`approve` via GET already removed), and the CSRF custom-header requirement on all POSTs.
- Static UI assets (`/`, `/app.js`, icons) are served unauthenticated in both modes, fixing the chicken-and-egg deadlock where the page asking for the token was itself token-protected.
- Startup prints an "Open-access mode" notice; app.js still prompts for a token on 401 when opt-in auth is enabled.
- Direct execution hardened: `python dashboard/server.py` bootstraps sys.path so it works from any CWD.

## [Previous] — Elite Review: Policy Evaluator Privilege-Escalation Fix

### Critical Security Fix
- **`runtime/policy.py` `_SafeEvaluator`**: YAML-style `true`/`false`/`null` literals in rule conditions were parsed as variable names. `flag == true` matched every action MISSING the flag (`None == None → True`). Concretely: `reversible == true → allow` auto-approved all write/edit/apply regardless of reversibility (privilege escalation), and deny rules like `tier-consequential-git-writes` falsely denied benign actions (e.g. ChatMessage "what is the status?"). Fixed via `_yaml_literals` mapping + fail-closed TypeError handling for membership checks on missing attributes. 13 regression tests added (`test_policy_evaluator_security.py`).

### Review Findings Fixed
- **CI validate.yml** type-checked nonexistent `cli.py`; corrected to `aizee_cli.py`.
- **RemoteA2AAdapter**: SSL context memoized (was reloading the system CA store on every poll tick).
- **Dashboard `/app.js` route** now covered by a test (content-type + body).

## [Previous] — Security Hardening + Quality Gates Zeroed + Docs Sync Automation

### Security Fixes (from full project audit)
- **[CRITICAL] Dashboard auth**: `dashboard/app.js` now sends `Authorization: Bearer` on every request; 401 prompts for the token (sessionStorage). The bundled UI previously only worked in ALLOW_NO_TOKEN mode.
- **[CRITICAL] approve-via-GET removed**: GET `/api/check` is dry-run only; `?approve=1` returns 400. Closes localhost CSRF privilege escalation.
- **[CRITICAL] Guardian fail-closed**: broken `guardian.authorize` now denies with `guardian_error` + audit log instead of silently allowing.
- **verify_ssl effective** (`aizee_mcp/adapters.py`): False builds a real unverified SSL context (+ init warning); previously returned None = default verified context.
- **A2A timeouts**: launch/poll pass `request_timeout` (default 30s) + SSL context; socket timeouts mark sessions failed instead of hanging the executor thread.
- **Stable vector ids**: non-UUID fallback hashes via blake2b (was salted `hash()` → orphaned vectors after restart).
- **Checkpoint thread-safety**: RLock around shared SQLite connection in `memory/checkpoint.py`.
- **Non-strict output validation hardened**: dropped `model_construct` bypass; invalid fields dropped then re-validated.
- **git_memory path safety**: category/entry_id validated against safe-component regex (blocks traversal).
- **CLI error handling**: friendly errors for malformed JSON args (check/run/policy/saga/mcp/agent); sync/graphify report failures instead of tracebacks/silent success; doctor passes project_root to Kernel.
- **SEO fallback registration**: manual MCP fallback now registers all 8 SEO tools.
- **Dashboard CSP**: script-src 'unsafe-inline' removed — JS moved to external `/app.js`, inline handlers replaced with addEventListener bindings.
- **Windows token ACL**: dashboard token file restricted via icacls (chmod is a no-op on Windows).

### Product Bugs Fixed
- **nofollow robots directive** now flagged by `seo_audit_page` (feature was tested but never implemented).
- **`multiple-h1` rule_id** test mismatch fixed (test expected nonexistent `h1-multiple`).
- **Guardian foreign defaults removed**: Monica's BaseService permission dependencies no longer shipped in core.

### Quality Gates → Green on main
- **mypy: 0 errors** across runtime/memory/aizee_mcp/config/cli/dashboard (268 files) — was 7 pre-existing.
- **ruff: 0 errors** repo-wide — was 13 pre-existing.
- **Full suite green** (~4,050 tests), coverage 96.26% (floor 80%). Previously-failing SEO network tests were real product bugs, now fixed with mocks intact.

### Architecture & Refactor
- **spec_engine.py (876 lines) split** into `runtime/spec/` package: models / engine / scaffold / analysis / templates. `runtime.spec_engine` remains a backward-compatible facade. Phase-gate logic deduplicated (`_phase_gate`), md5 finding ids → sha256.
- **Persona injection unified**: single `inject_persona_context()` in `runtime/persona.py` replaces 3 duplicated blocks (kernel/workflow_manager/workflow).
- **Read-only classification unified**: `PolicyManager._READ_ONLY_ACTIONS` derives from canonical `READ_ACTIONS` in `runtime/policy.py` (+ ChatMessage).
- **ChatManager implemented**: new `runtime/local_responder.py` answers status/budget/workflow/rules/skills/stack intents from live kernel state (zero tokens, honest offline label) instead of hardcoded "Acknowledged".

### Tooling & Docs
- **`scripts/sync_docs.py`**: counts + workflow routing table regenerated from filesystem truth; `--check` wired into CI validate workflow. Fixed AGENTS.md/spec.md stale counts (88→105 modules, 66→73 skills, 30→36 workflows, 162→163 stack refs), README duplicate table + missing rows (27, 33-35), double-listed memory-sync row.
- **pytest-timeout wired** (300s, thread method) guarding CI against hung tests.
- **True async tests added**: Guardian invoke/ainvoke decorators + A2A adapter executor path (real event loop, timeout/context assertions).
- **Conditional assertion fixed** in `tests/mcp/test_mcp_server.py` (seeded search results must exist and carry fields).
- **CONTRIBUTING.md added** (was referenced but missing): two-tier testing, code standards, module/skill/workflow recipes.
- Removed untracked `fetch-free-keys.py` (conflicted with supply-chain posture) + cleaned references.

## [Previous] — Governance Layer: Market Research + 10 Runtime Modules + 5 Skills + 3 Workflows

### Market Research (2026 AI Coding Governance)
- Analyzed Gartner Magic Quadrant for AI Governance Platforms (June 2026), Sonar State of Code (1,149 devs), Qodo AI Coding Paradox (500 eng), UserQ MENA (500 users), Eshal CX Benchmark (412 leaders).
- Key findings: 42% AI-committed code, 96% don't fully trust AI, 89% had AI production incidents, 28% Arabic churn in MENA, 24-point dialect gap.
- Identified 10 market gaps (G1-G10) and 6 direct competitors (repo-contract, Elastra, Salt Code, Fiddler, GitLab Duo, Databricks Unity Catalog).

### New Runtime Modules (10 added)
- **`runtime/rules_materializer.py`** — Emit aiZee rules → 7 tool formats (CLAUDE.md, .cursor/rules/*.mdc, .clinerules/*.md, .windsurfrules, .github/copilot-instructions.md, CONVENTIONS.md, .devin/rules/*.md). 6-scope precedence. Drift detection. (Closes G2)
- **`runtime/agent_gateway.py`** — LLM/MCP request-response interception. Pre-LLM + post-execution guardrails. ALLOW/REDACT/BLOCK verdicts. 3 built-in guardrails + custom registration. (Closes G1)
- **`runtime/plan_diff_validator.py`** — Plan + diff validation. AST import resolution, dependency guard, unrelated-refactor detection, test gap, forbidden paths. (Closes G3)
- **`runtime/composite_identity.py`** — Dual principal (agent + human) attribution. SHA-256 signature. Thread-safe registry. (Closes G4)
- **`runtime/supply_chain_guard.py`** — Undeclared import detection in 4 ecosystems (Python/Node/PHP/Go). AST + regex. Stdlib exclusion. (Closes G7)
- **`runtime/agent_catalog.py`** — Allowlist of permitted agents/flows/models. RBAC-gated. AgentStatus + ModelTier enums. (Closes G8)
- **`runtime/mcp_securable.py`** — MCP servers as governed securables with GRANT policies (USE/ADMIN/REGISTER). Tool allowlisting. (Closes G9)
- **`runtime/cost_attribution.py`** — Per-agent cost tags + anomaly detection (SPIKE/BUDGET_BREACH/UNEXPECTED_PROVIDER). (Closes G10)
- **`eval/reliability.py`** — reliability@k + security-adjusted reliability@k. Replaces misapplied pass@k. Multi-rollout scoring. (Closes G5)

### New Skills (5 lord-level)
- **`skills/arabic-dialect-lord/`** — 20 rules, 5 dialect families (Gulf/Egyptian/Levantine/Maghrebi/MSA), RTL, code-switching. Competitive moat for MENA. (Closes G6)
- **`skills/agent-governance-lord/`** — 20 rules, gateway enforcement stack, agent/flow/model allowlist, MCP-as-securable, composite identity.
- **`skills/eval-reliability-lord/`** — 18 rules, reliability@k + security-adjusted, multi-rollout mandatory, Docker reproducibility.
- **`skills/supply-chain-lord/`** — 19 rules, dependency guard, SBOM, Cosign, minimum release age, no floating ranges.
- **`skills/compliance-lord/`** — 16 rules, EU AI Act (Art. 9-15), NIST AI RMF, ISO 42001, risk tier classification.

### New Workflows (3 added)
- **`workflows/33-multi-tool-sync.md`** — 5-phase rules materialization (collect → resolve → materialize → drift detect → verify).
- **`workflows/34-agent-gateway-audit.md`** — 5-phase gateway audit (register → intercept requests → intercept responses → composite identity → audit report).
- **`workflows/35-reliability-eval.md`** — 5-phase reliability eval (prepare rollouts → classify → score → report → release gate).

### Updated
- `manifest.json`: +34 triggers, +10 features.
- `personas.yaml`: ARCH+agent-governance-lord+compliance-lord, QA+eval-reliability-lord, UX+arabic-dialect-lord, SEC+supply-chain-lord+agent-governance-lord, LEGAL+compliance-lord, ML+eval-reliability-lord, MLOPS+eval-reliability-lord, +25 keywords.
- `workflows/README.md`: 40 → 43 workflows.
- `runtime/__init__.py`: +34 re-exports.
- `tech-stack/useful-repos.md`: +16 governance/eval/Arabic repos.

### Tests
- 242 new tests across 9 test files. All PASS.
- Full suite: 3830 passed (275s).

### Quality Gates
- ruff: 0 errors. mypy: 0 errors. pytest: 3830 passed. graphify: 13217 nodes/27857 edges. memory ingest: 131 memories.

## [Previous] — Architectural Patterns Implementation (10 Patterns from 24 Top Repos)

### New Runtime Modules (3 added)
- **`runtime/middleware.py`** — Flat middleware pipeline (tRPC-style recursive `callRecursive`) + pre-compiled enhancer pipeline (NestJS-style guards/interceptors/pipes compiled once at registration).
- **`memory/checkpoint.py`** — Checkpoint state management with content-addressed snapshots (Dapr-style state store + LangGraph checkpoint pattern).
- **`memory/schema_contract.py`** — Contract-first schema verification with SHA-256 integrity hashing and drift detection (Prisma-style declarative schema model).

### Enhanced Existing Modules (7 modules extended)
- **`runtime/policy.py`** — Added `GuardrailResult`, `GuardrailRegistry`, `@input_guardrail`/`@output_guardrail` decorators (OpenAI Agents SDK tripwire pattern).
- **`runtime/guardian.py`** — Wired guardrails into `Guardian.authorize()` (input guardrails run before predicate rules; output guardrails via `check_output_guardrails()`).
- **`runtime/authorization.py`** — Added `ProtectedResource`, `Permission`, `ResourceRegistry` with AND/OR/DENY_OVERRIDE aggregate logic and negative permission inversion (Keycloak R→P→P decomposition).
- **`runtime/semantic_search.py`** — Added `hybrid_search()`, `fuse_rrf()`, `fuse_relative_score()` with alpha-blended fusion (Weaviate hybrid search pattern).
- **`memory/vector.py`** — Added `full_scan_threshold` for brute-force/indexed search selection + filter-during-traversal metadata filtering (Qdrant pattern).
- **`runtime/budget.py`** — Added `BudgetAction` enum (WARN/ALERT/REJECT), `BudgetWindow`, `BudgetWindowManager` for multi-window budget enforcement (Stripe/Lambda limits pattern).
- **`runtime/service_catalog.py`** — Added `CatalogEntity`, `CatalogStore`, `PluginRegistry`, `CatalogExtension` with typed relations and multi-index lookup (Backstage entity catalog pattern).
- **`runtime/agent_discovery.py`** — Added `discover_by_labels()` and `discover_by_capability()` for label/capability-based entity discovery.
- **`runtime/prompt_gate.py`** — Added `GradingResult`, assertion functions (`assert_equals`, `assert_contains`, `assert_no_pii`), PII/harm guardrails, adaptive rewriting (DSPy assertion-based prompt validation pattern).

### New Tests (10 files, 291 tests)
- `runtime/tests/test_middleware.py` — 31 tests (flat middleware + compiled pipeline).
- `runtime/tests/test_guardrails.py` — 20 tests (guardrail registry + decorators + Guardian wiring).
- `runtime/tests/test_resource_auth.py` — 31 tests (resource/permission/policy + aggregate logic).
- `runtime/tests/test_hybrid_search.py` — 30 tests (fusion strategies + hybrid search integration).
- `memory/tests/test_vector_search.py` — 29 tests (VectorStore + metadata filtering + operators).
- `memory/tests/test_checkpoint.py` — 22 tests (checkpoint state + content addressing).
- `memory/tests/test_schema_contract.py` — 21 tests (schema contract + drift detection + integrity).
- `runtime/tests/test_prompt_validation.py` — 41 tests (assertions + guardrails + adaptive rewriting).
- `runtime/tests/test_budget_window.py` — 44 tests (BudgetWindow + BudgetWindowManager + ALERT/REJECT).
- `runtime/tests/test_catalog.py` — 30 tests (CatalogEntity + CatalogStore + PluginRegistry + discovery).

### Architectural Patterns Adopted (10 patterns from 24 repos)
1. **Guardrail Tripwire** (OpenAI Agents SDK) — input/output guardrails with tripwire halting.
2. **Checkpoint State** (Dapr/LangGraph) — content-addressed state snapshots for resumable agents.
3. **Hybrid Search Alpha-Blended Fusion** (Weaviate) — parallel keyword+vector search with RRF/relative fusion.
4. **Flat Middleware Array** (tRPC) — recursive `callRecursive` execution with error wrapping.
5. **Pre-Compiled Enhancer Pipeline** (NestJS) — guards/interceptors/pipes compiled once at registration.
6. **Contract Schema with Hash Verification** (Prisma) — declarative schema contract with SHA-256 drift detection.
7. **Resource → Permission → Policy** (Keycloak) — fine-grained authorization with aggregate logic.
8. **Assertion-Based Prompt Validation** (DSPy) — grading results + guardrails + adaptive rewriting.
9. **BudgetWindow ALERT/REJECT** (Stripe/Lambda) — multi-window budget enforcement with severity escalation.
10. **Entity Catalog + Plugin Extensions** (Backstage) — versioned entity schema with typed relations and plugin registry.

### Quality Gates
- `ruff check .` — All checks passed.
- `mypy runtime/ memory/` — No issues (219 source files).
- `pytest` — Full suite passed, coverage 96.89%.
- `eval/harness.py` — `all_pass: true`.
- `validate-globals` — 324 scanned, 0 errors, version 5.5.0 consistent.

## [Unreleased] — Persona, Skill, Tech-Stack & Test Expansion

### New Personas (3 added — 19 → 22 total)
- **`DEVX`** — Developer Experience Engineer (developer portals, SDKs, CLIs, onboarding flows, ergonomics).
- **`MLOPS`** — ML Operations Engineer (model deployment, model registry, feature store, model serving, monitoring).
- **`FINOPS`** — Cloud Cost Optimization Engineer (cloud cost analysis, billing, budgets, reserved/spot instances, savings plans).

### New Skills (6 added — 64 → 68 total)
- **`api-versioning`** — API versioning strategies (header-based, URI-based, deprecation, backward compatibility).
- **`incident-commander`** — Incident command and response coordination (severity routing, comms, postmortems).
- **`code-reviewer`** — Multi-dimensional code review with confidence scoring and actionable feedback.
- **`migration-specialist`** — Database/framework migration planning, execution, and rollback safety.
- **`prompt-engineer`** — LLM prompt engineering (few-shot, chain-of-thought, structured output, eval harnesses).
- **`accessibility-auditor`** — WCAG/ADA accessibility auditing (ARIA, keyboard nav, contrast, screen reader compat).

### New Tech-Stack Files (70 added — 91 → 161 total)
- **AI/ML APIs**: OpenAI, Anthropic, Google AI, Cohere, Hugging Face, Replicate, Together AI, Groq.
- **DevOps**: Docker, Kubernetes, Helm, Terraform, Ansible, Pulumi, ArgoCD, Vault.
- **Vector DBs**: Pinecone, Weaviate, Qdrant, Milvus, Chroma, pgvector, LanceDB.
- **Frameworks**: FastAPI, Django, Flask, Express, NestJS, Spring Boot, Gin, Actix.
- **Data**: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, Kafka, RabbitMQ, ClickHouse.
- **Auth**: Keycloak, Auth0, Clerk, Supabase Auth, Okta, AWS Cognito.
- **Payments**: Stripe, PayPal, Square, Razorpay, Mollie, Adyen.
- **Deploy**: Vercel, Netlify, Railway, Fly.io, Render, Cloudflare Workers, AWS Lambda.
- **Languages**: Go, Rust, TypeScript, Kotlin, Swift, Elixir, Zig.

### Updated Tech-Stack Files (7 updated)
- `aizee-5.md`, `python-3.md`, `mcp-1.md`, `pytest-8.md`, `pydantic-2.md`, `tailwind-4.md`, `nextjs-15.md`.

### New Tests (9 files, 148 tests)
- Added 9 test files for previously untested runtime modules — 148 new tests covering edge cases, error paths, and integration scenarios.

### Updated Counts
- Personas: 19 → 22
- Skills: 64 → 68
- Tech-stack files: 91 → 161
- Runtime modules: 87 (unchanged)
- MCP tools: 35 (unchanged)
- Workflows: 30 (unchanged)

## [Unreleased] — Comprehensive Review & Cleanup (Multi-Persona Audit)

### Critical Fixes
- **Mojibake repair**: Fixed UTF-8 encoding corruption (UTF-8 misread as Latin-1/CP1252) across 6 files:
  - `manifest.json`: Arabic SEO triggers (2 keys repaired)
  - `README-AR.md`: 236 lines, 994 character repairs (full Arabic content restored)
  - `Memory.md`: 16 lines, 189 character repairs (emoji + Arabic restored)
  - `workflows/README.md`: 1 line, 3 repairs (≥ symbol restored)
  - `AGENTS.md`: 36 lines, 44 repairs (box-drawing + em-dash restored)
  - `.windsurfrules`: 4 lines, 4 repairs (em-dash restored)

### High Priority Fixes
- **Documentation drift**: Corrected stale module/skill/workflow/tool counts across 6 files:
  - Runtime modules: 60+ → 87 (in AGENTS.md, spec.md, README.md, docs/ONBOARDING_SRE.md, aizee-5.md)
  - MCP tools: 27 → 35 (in AGENTS.md, spec.md, README.md, aizee-5.md, docs/ONBOARDING_SRE.md)
  - Skills: 31 → 64 (in AGENTS.md, spec.md, README.md)
  - Numbered workflows: 36 → 30 (in AGENTS.md, spec.md, README.md)
- **Persona count**: Fixed `global-roles-ar.md` from "17 شخصية" → "19 شخصية"
- **Rule numbering**: Fixed duplicate rule #20 in `global-workflow.md` (second → #21)

### Medium Priority Fixes
- **Legacy naming**: Renamed `tech-stack/aios-5.md` → `tech-stack/aizee-5.md` + updated all references in Memory.md, CHANGELOG.md, and `runtime/tech_stack.py` alias map.
- **Prometheus metrics**: Renamed all `aios_*` metrics to `aizee_*` in `runtime/kernel.py` (6 counters/gauges), `runtime/metrics.py` (11 metric lines), and all related tests.
- **Stale .pyc cleanup**: Removed 317 stale bytecode files (including `aios_server.pyc`, `aios_cli.pyc`) with no corresponding `.py` source.
- **GSAP skill dedup**: Removed redundant `gsap-new/` and `gsap-refactor/` root wrapper directories (Claude Code-specific). `subskills/` is now the single canonical location.
- **Silent exception logging**: Added `logger.debug(..., exc_info=True)` to 5 silent `except Exception: pass/continue` blocks in:
  - `aizee_mcp/aizee_server.py` (tool import + registration + shutdown)
  - `aizee_mcp/tools/workflow_tools.py` (FTS search fallback)
  - `runtime/agent_discovery.py` (agent config parse)
  - `dashboard/server.py` (storage shutdown)

### Low Priority Additions
- **Manifest encoding tests**: New `tests/test_manifest_encoding.py` (4 tests) — validates manifest.json is valid JSON, free of mojibake, has Arabic triggers mapping to SEO audit workflow, and all trigger paths exist.
- **Workflow README count**: Updated `workflows/README.md` to accurately reflect 37 workflow files + 6 reference files (43 total).

### Quality Gates
- ruff: PASS (all checks)
- mypy: PASS (187 source files, 0 issues)
- pytest: PASS (all tests, 97% coverage)
- eval/harness: `all_pass: true`
- validate-globals: 0 errors, 0 warnings

## [5.5.0] — 2026-08-23 (15 Patterns from 15 Repos Study → aiZee Runtime)

### GitHub Repos Study v2 (15 repos analyzed: 5 Laravel + 5 Filament + 5 Node.js)
Deep analysis of top 15 GitHub repositories across Laravel (Invoice Ninja, Bagisto, Monica), Filament, and Node.js (Fastify, Prisma, Remix, NestJS, pnpm). Full report at `D:\server\temp\github-study-v2\REPOS_ANALYSIS_REPORT.md`.

### New Runtime Modules (5 files)
- **`runtime/commands.py`** (NEW): Command ABC + CommandBus with Saga-style rollback. Inspired by Invoice Ninja's `new MarkPaid()` pattern.
- **`runtime/scoped_manager.py`** (NEW): ScopedManager + ScopedRegistry + scoped_factory for context-isolated service instances. Inspired by Filament's `app()->scoped()` + Octane state flushing.
- **`runtime/hook_lifecycle.py`** (NEW): HookRegistry with 6 phases (pre_receive, pre_validation, pre_handler, post_handler, post_response, on_error). Inspired by Fastify's lifecycle hooks.
- **`runtime/layers.py`** (NEW): Layer IntEnum + LayerManifest for numbered package layering. Inspired by Prisma's numbered package prefixes.
- **`runtime/contract_emitter.py`** (NEW): ContractArtifact emitter (JSON schema + TypeScript stubs from Pydantic). Inspired by Prisma's contract-first design.

### New Script (1 file)
- **`scripts/generate_manifest.py`** (NEW): Auto-generate `runtime/__init__.py` re-exports from manifest. Inspired by Remix's `generate-remix.ts`.

### Deepened Existing Modules
- **`runtime/closure_evaluator.py`**: GuardianClosureEvaluator now resolves 14 param names (action, tool, attributes, context, request, decision, rule_name, reason, phase, user, tenant, session, user_id, tenant_id). Inspired by Filament's automatic DI.
- **`runtime/__init__.py`**: +15 re-exports for new modules.
- **`scripts/guard_invariants.py`**: +3 new checks (no_magic_strings, trait_composition, manifest_drift).

### New Tests (89 tests)
7 new test files: `test_commands.py` (13), `test_scoped_manager.py` (14), `test_hook_lifecycle.py` (10), `test_layers.py` (12), `test_contract_emitter.py` (13), `test_generate_manifest.py` (11), `test_closure_evaluator_deepened.py` (16).

### Documentation Updates
- **`tech-stack/filament-4.md`**: +5 rules (Schema separation, sub-navigation, global search, scoped managers, path generators).
- **`tech-stack/filament-5.md`**: +5 rules (Page-based UI, enum traits, minimal plugins, view hooks, asset publishing).
- **`tech-stack/laravel-12.md`**: +5 rules (Command objects, custom casts, fluent chaining, package modularity, search abstraction).
- **`tech-stack/laravel-13.md`**: +4 rules (PHP 8 attributes, contract-first artifacts, state flushing, app warming).
- **`tech-stack/useful-repos.md`**: +10 entries (Laravel/Filament/Node.js tools + reference repos).
- **`tech-stack/laravel-ai-workflow.md`** (NEW): 8 rules for Boost + Compass + FilaCheck pipeline.
- **`skills/backend-frameworks-lord/SKILL.md`**: +7 rules (all 15 patterns).
- **`workflows/29-filament-ai-workflow.md`** (NEW): 15 rules for AI-assisted Filament dev.
- **`workflows/README.md`**: Updated count.
- **`manifest.json`**: +5 triggers, +6 features.

### Quality Gates
- ruff ✅ (0 errors), mypy ✅ (0 errors, 220 source files), pytest ✅ (982 tests, 97% coverage), guard_invariants ✅ (all checks passed), validate-globals ✅ (0 errors, 0 warnings), eval/harness.py ✅ (all_pass: true).

## [5.4.0] — 2026-08-21 (SEO Integration: 5 Repos + 5 Tools Study → aiZee)

### SEO Study (5 GitHub repos + 5 building blocks analyzed)
Deep analysis of top 5 SEO GitHub repositories + 5 SEO tools/building blocks. Full reports at `D:\server\temp\seo-study\SEO_REPORT.md` + `D:\server\temp\seo-study\SEO_INTEGRATION_REPORT.md`.
- **Repos**: claude-seo (14K stars, parallel agent delegation), open-seo (12K stars, 46 MCP tools), crawlseo (495 stars, GSC+crawler), seo-audit-skill/SEOmator (377 stars, 251 rules), rustyseo (312 stars, Rust log analysis).
- **Building blocks**: GSC API (free official), DataForSEO (paid SERP), Playwright (JS rendering), Common Crawl (free backlinks), Lighthouse/PSI API (free CWV).

### Phase 1 — seo-lord Skill (NEW, directory layout with 7 references + 2 templates)
- **`skills/seo-lord/SKILL.md`**: 20 rules (grounding in Google primary sources, progressive disclosure, parallel analysis, falsifiability-first recommendations, confidence-weighted aggregation, health score 0-100, 251 audit rules, CWV INP-not-FID, schema active/deprecated, GEO/AEO citability, crawl budget, LLM-safe output, free APIs first).
- **`skills/seo-lord/references/`**: 7 files — technical-seo (9 categories), content-eeat (E-E-A-T framework), schema-types (active/deprecated/keep), geo-aeo (AI search optimization), cwv-thresholds (LCP/INP/CLS + measurement), audit-rules (251 rules/20 categories), health-scoring (0-100 algorithm).
- **`skills/seo-lord/templates/`**: 2 files — seo-audit-report, content-brief.
- **`personas.yaml`**: Registered seo-lord as lord skill (40 keywords incl. Arabic). Linked to ARCH, DEV, UX, DOC personas.

### Phase 1 — tech-stack/seo-1.md (NEW)
- 35 rules covering: meta tags, canonical, sitemap, robots.txt, hreflang, JSON-LD schema (active/deprecated), Core Web Vitals (INP replaced FID), URL structure, mobile, security, redirects, images, content quality, E-E-A-T, internal links, GEO/AEO, crawl budget, indexing, IndexNow, social meta, HTML validation, accessibility, JS SEO, health score, audit rules, SEO opportunities, local SEO, e-commerce, international, output formats, falsifiability, prohibitions, free/paid APIs.

### Phase 1 — useful-repos.md + tech_stack.py
- **`useful-repos.md`**: +10 entries (5 SEO repos + 5 SEO building blocks).
- **`runtime/tech_stack.py`**: +10 SEO package aliases (seo, laravel-filament-seo, spatie/laravel-sitemap, artesaos/seotools, etc.).

### Phase 2 — Workflow 27 (NEW)
- **`workflows/28-seo-audit.md`**: 21 rules (detect business type, scope, batch crawl, technical SEO, CWV via PageSpeed API, content E-E-A-T, schema validation, GEO/AEO readiness, links, images, health score, 251 audit rules, GSC data, opportunities, Markdown output, falsifiability, primary-source grounding, LLM-safe output, prohibitions, quality gate, MCP tools).
- **`manifest.json`**: +7 trigger entries (seo audit, seo analysis, search optimization, seo, سيو, تحسين محركات البحث, /seo-audit).
- **`workflows/README.md`**: Updated count 27 → 28, added SEO audit row.

### Phase 3 — MCP SEO Tools (NEW, 8 tools, stdlib only)
- **`aizee_mcp/tools/seo_tools.py`**: 8 tools using only Python stdlib (urllib, html.parser, re, json):
  - `seo_audit_page`: Single page audit (meta, headings, schema, canonical, images, content, health score).
  - `seo_audit_site`: Full site crawl (up to 2000 pages, batch crawler 15 concurrent, aggregate score).
  - `seo_check_cwv`: Core Web Vitals via PageSpeed Insights API (free, no key required).
  - `seo_validate_schema`: JSON-LD extraction + active/deprecated classification.
  - `seo_analyze_content`: E-E-A-T + Flesch readability + citability + word count.
  - `seo_check_geo`: AI search readiness (AI crawler access, semantic HTML, llms.txt, schema).
  - `seo_get_gsc_data`: GSC data (returns OAuth setup instructions if no credentials).
  - `seo_find_opportunities`: Striking distance, low CTR, cannibalization from GSC data.
- **`aizee_mcp/tools/schemas.py`**: +3 schemas (SeoAuditSchema, SeoCwvSchema, SeoSchemaSchema).
- **`aizee_mcp/tools/__init__.py`**: Added register_seo_tools + 3 schema exports.
- **`aizee_mcp/API.md`**: Added "SEO Tools" section (8 tool docs).
- **`pyproject.toml`**: Added seo_tools to mypy untyped-decorator override.
- **`tests/mcp/test_seo_tools.py`** (NEW): 132 tests — all passing.

### Quality Gates
- ruff ✅ (0 errors), mypy ✅ (0 errors), pytest ✅ (132/132 SEO tests + 893/893 total tests passed), MCP auto-discovery ✅ (8 SEO tools registered).
- 5-persona review rounds 3+4 (ARCH + DEV + QA + SEC + DOC): all issues fixed (SSRF via redirects, DNS rebinding, 0.0.0.0, empty @graph, @graph as dict, empty lighthouseResult, empty body, empty rows, charset handling, nested tags, syllables, position=0, deque, compiled regexes, paragraph splitting, nofollow+viewport checks, tel/MAILTO filtering, robots.txt \r\n, cannibalization dedup, TTFB int, cached opener, relative redirect resolution).

## [5.3.0] — 2026-08-19 (Laravel/Filament Tech-Stack Enrichment + Runtime Improvements)

### GitHub Repos Study (10 repos analyzed)
Deep analysis of 10 leading GitHub repositories (5 Laravel + 5 Filament) cloned to `D:\server\temp\github-study\`. Full report at `D:\server\temp\github-study\REPOS_ANALYSIS_REPORT.md` (627 lines).
- **Laravel repos**: Bagisto (eCommerce/Concord), Monica (CRM/DDD), Krayin (Modular/MagicAI), BookStack (Wiki/Activity), Koel (Music/Repository+DTO+API)
- **Filament repos**: Filament (framework/Plugin system), SuperDuper Starter Kit (Clusters/12 plugins), Lara-Zeus Sky (CMS/Status enum), MVPable (SaaS/DDD+Actions), Filament-Blog (Faceless/trait-based)

### Phase 1 — Tech-Stack Updates (4 files)
- **`laravel-12.md`**: 10 rules (Repository, Service Layer, DTO, Three-Component Model, Activity Logging, UUID, DDD)
- **`laravel-13.md`**: 12 rules (PHP 8.4 asymmetric visibility, Context API, AI vector search, Custom Builders/Casts, API Resources + Structure Constants, Header-based Versioning, Cursor Pagination, Contracts, License Gating)
- **`filament-4.md`**: 17 rules (Tab-based Forms, Status Enum, Upload/URL Toggle, Configurable Editor, Navigation Badges, Custom Permission Prefixes, Role-based Visibility, Dynamic Branding, Discovery, Authorization, Action Groups, Search Highlighting)
- **`filament-5.md`**: 20 rules (Islands, Async/Defer, Scoped styles, Static Props fix, HasAvatar, CSP-safe build, Schema Pattern, Plugin System, Cluster, ComponentManager, EvaluatesClosures, Macroable, Registry, NavigationManager, Asset Management, Multi-DB Testing, Spatie Media/Tags)

### Phase 2 — New Tech-Stack Files (3 files)
- **`laravel-testing.md`** (NEW): 18 rules (Pest 3+, Two-Tier Testing, Factories, Helper Traits, Custom Assertions, Security Tests, License Mocking, Translation, E2E Playwright, Multi-DB, Parallel, Browser, API Structure, Cursor Pagination, Bus Faking, AAA, Coverage)
- **`laravel-security.md`** (NEW): 25 rules (Sanctum/Fortify/Jetstream/WebAuthn, 2FA, ACL, Multi-Tenancy, Content Filtering, SVG Sanitization, Rate Limiting, Security Headers, ForceHttps, Installer Lockdown, Disposable Email, GDPR, Impersonation, UUID, License Gating, SEC-01 to SEC-10)
- **`filament-plugins.md`** (NEW): 14 rules (Plugin Interface, Registration, Boot Order, Authorization, 12+ Recommended Plugins, Custom Development, Discovery, Configuration, Testing, Theming, Assets, Navigation, Multi-Tenancy, Compatibility)

### Phase 3 — Skill Updates (3 files)
- **`backend-frameworks-lord/SKILL.md`**: 20 rules (IDs for Context7, 4-level Architecture Patterns, Pattern Selection Matrix, Service/Repository/DTO/API/Multi-Tenancy rules, Three-Component Model, Activity Logging, AI Integration, Testing/Security cross-refs)
- **`page-sections-lord/SKILL.md`**: 32 rules (Status Enum, Tab-based Forms, Upload/URL Toggle, Configurable Editor, Navigation Builder, Search Highlighting, Spatie Media/Tags, Password Protection, Sticky/Scheduling, Parent-Child, FAQ/Breadcrumb/Article/Organization Schema, Action Groups, Navigation Badges, Create Option Forms, Auto-slug)
- **`useful-repos.md`**: 65 rules (10 new Laravel + Filament repos added to existing list)

### Phase 4 — New Workflows (3 files)
- **`24-laravel-architecture-setup.md`** (NEW): 22 rules (complexity detection, Service/Repository/DTO/DDD scaffolding, Custom Builders/Casts/Contracts, Actions, Modular Concord, Three-Component, Activity Logging, UUID, Context7 query, composer commands, test commands)
- **`25-filament-plugin-development.md`** (NEW): 22 rules (plugin class creation, register/boot lifecycle, config, authorization, configureUsing, assets, multi-tenancy, navigation, theming, Context7 query, scaffold commands, test commands, compatibility, documentation)
- **`26-laravel-api-versioning.md`** (NEW): 24 rules (RouteServiceProvider, loadVersionAwareRoutes, base + versioned route files, API Resources with Structure Constants, cursor pagination, versioned controllers, deprecation headers, OpenAPI docs, Context7 query, scaffold commands, test commands, backward compatibility)

### Phase 5 — Runtime Improvements (4 files)
- **`runtime/plugin.py`**: Two-phase lifecycle `register()` + `boot()` (Filament pattern). `PluginSandboxError(AizeeError)` replaces `RuntimeError`. Split `load_all()` into `_register_phase` + `_boot_phase`.
- **`runtime/closure_evaluator.py`** (NEW): `ClosureEvaluator` with automatic dependency injection (Filament EvaluatesClosures pattern). Resolution order: named → typed → default → evaluation_identifier → default value → None → error. `GuardianClosureEvaluator` subclass. `ClosureResolutionError(AizeeError)`.
- **`runtime/guardian.py`**: `permission_dependencies` system (Monica BaseService pattern). `authorize()` auto-validates dependencies on ALLOW decisions. `PolicyDeniedError` replaces `PermissionError`. Constants: `EVALUATION_ERROR_REASON`, `NO_MATCHING_RULE_REASON`, `DEFAULT_RULE_NAME`.
- **`aizee_mcp/tools/schemas.py`** (NEW): JSON_STRUCTURE constants for MCP tool responses (Koel pattern). 7 schema classes + `PaginatedResultSchema` + `ALL_SCHEMAS` registry.

### Phase 6 — Bug Fixes + Lint Cleanup (52 → 0 errors)
- **ruff**: Fixed 52 errors across `runtime/`, `aizee_mcp/`, `memory/`, `scripts/`, `eval/` (I001, F401, F811, UP017, SIM105/110/114, RUF001/002/003)
- **mypy**: Fixed 30 `untyped-decorator` errors via `pyproject.toml` override for 4 MCP tools modules
- **adapters.py**: Fixed `asyncio.TimeoutError` not caught in `poll()` (Python 3.10 compat)
- **test_vibe.py**: Fixed unrealistic `latency_ms > 0` assertion for instant mock agents
- **git_memory.py**: Fixed mojibake box-drawing characters in docstring
- **migrations.py + spec_engine.py**: Fixed mojibake unicode arrows (→) in docstrings/strings
- **_compat.py**: Added `# pyright: ignore` directives for try/except MCP SDK imports
- **pyproject.toml**: Added `UP017` to ruff ignore list (Python 3.10 compat — `datetime.UTC` requires 3.11+)

### Tests
- **45 new tests**: `test_closure_evaluator.py` (23), `test_mcp_schemas.py` (14), 5 authorize() auto-validation tests, 4 two-phase lifecycle tests
- **Test fixes**: `test_plugin_guard.py` + `test_guardian.py` updated for `PluginSandboxError`/`PolicyDeniedError`
- **Coverage**: 96.88% (all new files at 100%)
- **Total**: 2773 passed, 2 skipped, 0 failed

### 3-Persona Review (ARCH + DEV + QA-SEC)
- **ARCH**: 14/14 files verified (tech-stack + skills + workflows + README)
- **DEV**: 18/18 files verified (runtime + MCP + tests + configs)
- **QA-SEC**: 12/12 points verified (security + integration + bug fixes + tests)

### Version
- Version bumped to 5.3.0 across `pyproject.toml`, `manifest.json`, `.aizee-version`, `README.md`, `README-AR.md`, `aizee_mcp/API.md`, `validate-globals.py`, `validate-globals.ps1`.

## [5.2.0] — 2026-08-18 (Fourth Audit — External Research-Driven Improvements)

### P0 — Critical Startup Fixes
- **budget.json encryption corruption**: `BudgetManager._load()` catches `InvalidToken` + JSON errors, quarantines corrupt file to `.corrupt.bak`, falls back to defaults
- **mcp FastMCP→MCPServer shim**: `aizee_mcp/_compat.py` re-exports `FastMCP`/`Resource` from new locations after upstream rename

### P1 — New Safety Layers
- **MCP Firewall** (`runtime/mcp_firewall.py`): per-tool-call access control with `allow`/`deny`/`require_approval`, priority-ordered rules, safe AST condition evaluation
- **Loop Detector** (`runtime/loop_detector.py`): hash-based loop detection with sliding window, integrated into `Kernel.act()`

### P2 — Pre-inference + Lifecycle Safety
- **Prompt Gate** (`runtime/prompt_gate.py`): deterministic pre-inference prompt safety scanner (injection, system-override, destructive, exfil, privilege)
- **Trajectory Tracker** (`runtime/trajectory.py`): run-level trajectory tracking with stall detection
- **Approval Service** (`runtime/approval_service.py`): persistent approval lifecycle + multi-channel notifications

### P3 — Tooling + Observability
- **Reasoning Graph** (`runtime/reasoning_graph.py`): directed graph for multi-step governance escalation chains
- **Context Manager** (`runtime/context_manager.py`): 3-level context trimming with atomic group preservation
- **Agent Discovery** + `aizee agents discover` CLI + `aizee skill eject` CLI
- **Guard Invariants** (`scripts/guard_invariants.py`): mechanical code-invariant checks

### P4 — Polish
- **Dashboard theming**: light/dark/auto theme toggle with localStorage persistence
- **4-tier testing**: `workflows/testing-tiers.md` upgraded to FAST/SMOKE/FULL/VIBE
- **Vibe testing** (`eval/vibe.py` + 9 scenarios): LLM-graded behavioral scenarios

### Version
- Version bumped to 5.2.0 across `pyproject.toml`, `manifest.json`, `.aizee-version`, `README.md`, `README-AR.md`, `aizee_mcp/API.md`, `validate-globals.py`, `validate-globals.ps1`.

## [5.1.0] — 2026-08-18 (Third Audit — Hardening & Polish)

### P0 — Critical
- **Dockerfile fixed**: `cli.py` → `aizee_cli.py` (file didn't exist), Python 3.11 → 3.14
- **Exception hierarchy unified**: `GuardrailViolationError`, `ApprovalRequiredError`, `IssueTrackerError`, `MetricNameError`, `MetricDuplicationError`, `LabelValueError` now all inherit from `AizeeError`
- **aizee shim PATH fix**: `update.py` now adds user Scripts dir to PATH on Windows

### P1 — High Priority
- **CI matrix**: Python 3.13 + 3.14 added to test matrix
- **aizee_mcp/API.md version**: Synced to 5.2.0
- **Secure-by-default encryption**: `_get_fernet()` auto-generates key if none set; `AIOS_ENCRYPTION_KEY=plaintext` for explicit opt-out
- **Dashboard token hardened**: `chmod 0o600` on token file
- **Graceful shutdown**: Dashboard + MCP server flush storage + close DB on SIGTERM/SIGINT
- **Log rotation**: `audit.log` + `telemetry.jsonl` rotate at 100MB (5 rotated logs kept)
- **test_chat_manager.py**: 23 new tests for ChatManager
- **Mock time in tests**: `time.sleep()` is no-op in fast tier (autouse fixture)
- **Self-healing integrated**: `AgentManager.check_agents_health()` + `respawn_agent()`

### P2 — Medium
- **StorageBackend explicit conformance**: `InMemoryStorage`, `JsonFileStorage`, `SqliteStorage`, `MemoryStoreAdapter` explicitly inherit `StorageBackend`
- **.env allowlist**: Only known env vars loaded from `.env` files (security)
- **Audit redaction**: Key-based redaction added (not just value-based)
- **CSP strengthened**: `object-src 'none'`, `base-uri 'self'`, `frame-ancestors 'none'`
- **NumPy range tightened**: `>=1.26.0,<2.0`
- **KernelBuilder**: Fluent builder for dependency injection
- **MCP client async/sync unified**: `call_tool` delegates to `async_call_tool` via `asyncio.run()`
- **Test organization**: 10 test files moved from `tests/runtime/` to `runtime/tests/`
- **Weak assertions fixed**: `test_p3_features.py` + `test_dynamic_persona.py`
- **DB connection pooling**: `BaseRepository` pools SQLite connections (pool size 5)
- **DB backup automation**: `--schedule daily/hourly` + `--verify` flag
- **Operational docs**: `docs/OPERATIONS.md`, `docs/DEPLOYMENT.md`, `docs/ONBOARDING_SRE.md`

### P3 — Low
- **Rate limit LRU eviction**: Evict oldest entries when approaching max
- **Plugin sandbox strengthened**: Blocked `__import__`, `globals`, `locals`, `vars`, `dir`, `type`, `classmethod`, `staticmethod`, `literal_eval`
- **Plugin resource-based permissions**: Glob patterns (`Write:/tmp/*`)
- **MCP tool auto-discovery**: Scans `aizee_mcp/tools/*_tools.py`
- **Parametrized tests**: Added more `@pytest.mark.parametrize` coverage
- **Dashboard HTTP logging**: 4xx/5xx logged to stderr
- **K8s secret warning**: Comment added to placeholder
- **Migration rollback**: `MigrationRunner.rollback(version)` with rollback functions

### Version
- Version bumped to 5.2.0 across `pyproject.toml`, `manifest.json`, `.aizee-version`, `README.md`, `README-AR.md`, `aizee_mcp/API.md`, `validate-globals.py`, `validate-globals.ps1`.

## [Unreleased] — 2026-08-18 (Second Audit)

### Fixed — Critical Issues (P0)
- **`cryptography` version mismatch**: Upper bound raised `<46.0` → `<52.0` to accommodate installed 50.0.0. `pip check` no longer warns.
- **`guardian.yaml` missing**: Created `runtime/policies/guardian.yaml` with 10 rules (deny rm -rf, force push, reset --hard, DROP TABLE, eval/exec; require approval for deploy, git push, curl, pip install; deny secret exfil). Guardian gate now active from day 1. Added `regex` operator to `_PredicateEvaluator`.
- **`capabilities: []` empty**: `AgentCapabilities.__init__` now grants 5 default capabilities (read, write, exec, deploy, destructive). `kernel.status()` reports meaningful capabilities. Added `revoke()` method + `defaults=False` option for empty init.
- **`probity.yaml` missing**: Created `runtime/policies/probity.yaml` with 13 rules (block rm -rf, force push, reset --hard, dd, mkfs, chmod 777, curl|bash; block hardcoded secrets, eval, pickle, shell=True, f-string SQL; enforce kebab-case). Probity integrity layer now active.

### Changed — Python 3.14 Targets (P1)
- **`ruff target-version`**: `py310` → `py314`. Enables 3.14-specific linting.
- **`mypy python_version`**: `3.12` → `3.14`. Enables 3.14-specific type checking.
- **`pyproject.toml` classifiers**: Added `Programming Language :: Python :: 3.13` and `3.14`.
- **`ruff` ignore list**: Added `UP042` (str+Enum → StrEnum, needs refactoring) and `UP046` (Generic class type params).

### Added — MemoryStore Public API (P1)
- **`MemoryStore.count()`**: Returns total memory count (public method).
- **`MemoryStore.list_all(kind=None, limit=1000)`**: Lists memories, optionally filtered by kind, most recent first.
- **`MemoryStore.delete_hard(mem_id)`**: Hard-deletes a memory (row + vector). Returns True if existed.
- **`MemoryStoreAdapter` refactored**: Now uses public API only — no more `_conn()`/`_row_to_memory()` private access.

### Added — Test Cleanup + Env Template (P1)
- **`conftest.py` autouse fixture**: `gc.collect()` after each test to close leaked SQLite connections. Reduces `ResourceWarning: unclosed database` warnings.
- **`BaseRepository.close()`**: Added no-op `close()` method for resource cleanup interface.
- **`.env.example`**: Template with all env vars (AIZEE_ROOT, AIOS_ENCRYPTION_KEY, dashboard, Sentry, Upwork, Freelancer, LinkedIn, Graphify).

### Added — CLI Commands + Dashboard (P2)
- **`aizee doctor` expanded**: 7 new checks — guardian.yaml (10 rules), probity.yaml (13 rules), capabilities (5), tech_stack detection (7 entries), cryptography version match, .env.example template. 33 total checks.
- **`aizee memory ingest --watch`**: Auto re-ingests when tech-stack/, rules/, or workflows/ files change. Polls every 2s, Ctrl+C to stop.
- **`aizee spec` CLI**: New command with `list`, `analyze`, `converge`, `scaffold` subcommands. Exposes SpecEngine from terminal (was MCP-only).
- **Plugin auto-discovery**: `PluginManager._discover_plugins()` now auto-loads all `plugins/*/` with valid `__init__.py` when `plugins.yaml` is missing or empty. Previously required explicit listing.
- **`aizee audit` CLI**: New command with `show` (filtered by type/limit) + `verify` (hash chain integrity). Added `AuditLogger.read_entries()` method.
- **Dashboard SSE stream expanded**: Now includes agents, guardian_rules, capabilities, tech_stack (was: version/budgets/metrics only).

### Quality Gate
- ruff ✅, mypy ✅ (174 source files), pytest ✅ (2544 passed, 0 failed, 1 skipped tkinter, 96.42% cov), eval/harness ✅ `all_pass: true`, validate-globals ✅ 0 errors.

## [Unreleased] — 2026-08-18

### Fixed — Python 3.14 Compatibility (P0)
- **`test_guardian.py`**: Replaced `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` (4 tests). `get_event_loop()` removed in Python 3.14.
- **`test_rate_limiter.py`**: Changed `== 7.0` to `pytest.approx(7.0, abs=0.01)` for float comparison (time drift caused flaky failure: `7.000004053115845 != 7.0`).
- **`test_spec_engine.py`**: exec globals now includes `__file__` to prevent `NameError` when module-level code references `Path(__file__)`.
- **`test_uninstaller_gui.py`**: Added `pytest.importorskip("tkinter")` to prevent collection break on headless/Python 3.14 Windows where tkinter is unavailable.

### Added — Internal Tech-Stack References (P1.1, Dogfooding)
- 7 new `tech-stack/*.md` files for aiZee's own stack: `python-3.md`, `aizee-5.md`, `pydantic-2.md`, `mcp-1.md`, `pytest-7.md`, `pytest-8.md`, `pyyaml-6.md`, `rich-13.md`.
- **`runtime/tech_stack.py`**: `_parse_pyproject_toml()` now registers the project self-name + version and extracts `requires-python` version. Added `aizee` → `aios` alias.
- **Result**: `get_os_status` MCP tool and `kernel.detect_tech_stack()` now return 7 tech_stack entries instead of empty `{}`. aiZee now satisfies `[VER-01]` for itself.

### Changed — Smart Policy Fallback (P1.2)
- **`runtime/policy.py`**: `PolicyEngine.evaluate()` now classifies unmatched actions by type instead of using blanket `default_action`:
  - Read actions (view, read, grep, search, status, etc.) → `allow`
  - Write actions (edit, write, deploy, exec, etc.) → `ask`
  - Destructive actions (rm, delete, truncate, drop, etc.) → `deny`
  - Unknown actions → `ask` (conservative)
  - YAML `default_action=deny` still wins as strict override.
- 4 new tests in `test_policy.py` for classification logic.

### Changed — asyncio 3.14 Compatibility (P1.3)
- **`aizee_mcp/adapters.py`**: `asyncio.get_event_loop()` → `asyncio.get_running_loop()` (4 occurrences in `RemoteA2AAdapter.launch/poll`). Correct API for use inside async functions.
- **`runtime/guardian.py`**: `asyncio.iscoroutinefunction()` → `inspect.iscoroutinefunction()` (deprecated in 3.14, removed in 3.16).
- **`tests/mcp/test_adapters.py`**: Updated 9 mock patches from `asyncio.get_event_loop` to `asyncio.get_running_loop`.

### Added — StorageBackend ↔ MemoryStore Bridge (P1.4)
- **`runtime/storage_backend.py`**: New `MemoryStoreAdapter` class that wraps `MemoryStore` to implement the `StorageBackend` protocol. Enables new code using `StorageFactory` to access the rich `MemoryStore` (SQLite + FTS5 + vector) through the uniform interface. Supports `put` (dict or Memory), `get`, `delete` (soft via invalidate), `scan` (optionally filtered by kind), `keys`, `count`, `clear`, and no-op `flush`/`load`.
- 12 new tests in `test_storage_backend.py` (`TestMemoryStoreAdapter`).

### Fixed — `__file__` Robustness in `__main__` Blocks (P2.1)
- 3 runtime modules (`tree_sitter_provider.py`, `semantic_search.py`, `codegraph.py`) now guard `Path(__file__)` in `__main__` blocks with `"__file__" in globals()` fallback. Prevents `NameError` when exec'd without `__file__` in globals.
- `spec_engine.py` already fixed in P0.3 with module-level guard.

### Quality Gate
- ruff ✅, mypy ✅, pytest ✅ (2527+ passed, 0 failed, 1 skipped tkinter), tech_stack detection returns 7 entries.

## [Unreleased] — 2026-08-17

### Added — Architecture Patterns from spec-kit + Floci
- **Spec-driven templates** (`tech-stack/spec-driven-templates/`): 5 templates (spec, plan, tasks, constitution, checklist) adapted from GitHub spec-kit. Used by `SpecEngine.scaffold_spec/plan/tasks/checklist()`.
- **Spec cross-artifact analysis** (`SpecEngine.analyze_artifacts()`): detects coverage gaps, ambiguity (vague terms without measurable criteria), underspecification ([NEEDS CLARIFICATION]/TODO markers), and constitution violations. Read-only. Workflow `22-spec-analyze.md`.
- **Spec-to-code convergence** (`SpecEngine.converge_to_code()`): assesses codebase against spec/plan/tasks, classifies gaps as missing/partial/contradicts, suggests remediation tasks. Read-only. Workflow `23-spec-converge.md`.
- **Constitution system** (`SpecEngine.set_constitution()` + `validate_checklist()`): per-spec governing principles with MUST/SHOULD enforcement.
- **Pluggable storage backend** (`runtime/storage_backend.py`): `StorageBackend` protocol + 3 implementations (InMemoryStorage, JsonFileStorage, SqliteStorage) + `StorageFactory` with path-based caching and lifecycle management (load/flush/shutdown). Inspired by Floci's `StorageBackend<K,V>` + `StorageFactory`. 41 tests.
- **Multi-index service catalog** (`runtime/service_catalog.py`): `ServiceDescriptor` (frozen dataclass) + `ServiceCatalog` with 6 indexes (by_name, by_kind, by_persona, by_trigger, by_tech_stack, by_lord) + `match_trigger()`/`match_tech_stack()` for ranked text matching + `build_catalog_from_directory()`. Inspired by Floci's `ServiceCatalog`. 28 tests.
- **AizeeError hierarchy** (`runtime/schemas.py`): `AizeeError` base + `PolicyDeniedError`, `BudgetExceededError`, `ValidationError`, `StorageError` subclasses. Each carries `error_code`, `severity`, `context` dict. `to_dict()` for structured logging. Inspired by Floci's `AwsException`.
- **PaginatedResult** (`runtime/schemas.py`): `items` + `next_token` + `total` dataclass for paginated list operations. `to_dict()` + `has_more` property. Inspired by Floci's `PaginatedResult<T>`.
- **AGENTS.md expanded** with Floci-style sections: Architecture, Package Layout, First Principles, Adding a New Runtime Module/Skill/Workflow, Error Handling, Storage Rules, Common Mistakes, Human Handoff, Code Style, Logging, PR Guidelines.

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
