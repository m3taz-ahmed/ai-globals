# aiZee — Review Findings & Fix Plan

Generated: 2026-08-06
Scope: comprehensive review of `D:\server\.ai` (aiZee v4.22.0)
Personas: ARCH, PRODUCT, QA, SRE, SEC, DEV, PERF, DOC

---

## Executive Summary

- All quality gates pass before and after the initial batch of fixes.
- 5 concrete fixes already applied and staged.
- 40+ additional issues identified across runtime, memory/MCP, dashboard, DevOps, rules/skills, and documentation.
- This file tracks the findings and the recommended fix order for continuation in later sessions.

---

## Applied Fixes

- `manifest.json`: version 4.21.0 -> 4.22.0, updated date, added `cleanup`/`scm` triggers.
- `config.py`: default version 4.21.0 -> 4.22.0.
- `runtime/mcp_client.py`: clientInfo version 4.21.0 -> 4.22.0; added `_send` timeout; tightened `parse_mcp_command` validation.
- `pyproject.toml`: added `temp/` to ruff and mypy excludes (fixes `mypy .`).
- `runtime/approval_cache.py`: locked `is_approved()` to avoid race condition.
- `memory/store.py`: WAL mode, busy timeout, connection lock, and improved FTS5 sanitization.
- `memory/vector.py`: log embedding failures instead of swallowing `RuntimeError`.
- `aios_mcp/aizee_server.py`: locks on singleton kernel/memory; stricter name/path validation; symlink/UNC traversal defence.
- `dashboard/server.py`: added CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy headers.
- `dashboard/index.html`: added `escapeHtml` helper and escaped all server-rendered dynamic content.
- `runtime/workflow.py`: WAL/lock for SQLite; exception handling around `act()` and `McpClient.call_tool()`.
- `runtime/saga.py`: WAL/lock for SQLite.
- `runtime/tech_stack.py`: logging for parser failures; safer semver extraction in `_clean_version`.
- `runtime/audit.py`: redact sensitive keys before writing audit log.
- `README.md` / `workflows/README.md`: corrected badge and file counts.
- `workflows/code-quality.md` / `rules/vocabulary.md`: standardized max args to 4.
- `Dockerfile`: pinned to `python:3.11.9-slim`; added state volumes.
- `install.sh`: `set -euo pipefail`; Python 3.10+ version check.
- `install.ps1`: Python 3.10+ version check; backup before overwriting agent configs.
- `runtime/tests/test_workflow.py`: new tests for workflow run, load, and MCP parse.

---

## SWOT

### Strengths
- Strong symbolic rule system (vocabulary, anti-patterns, skills).
- Comprehensive persona/skill/workflow system.
- Quality gates enforced (ruff, mypy, pytest, harness).
- Good separation between runtime, memory, aios_mcp, dashboard.
- High test coverage for kernel, rule_frontmatter, memory.

### Weaknesses
- `Kernel` is a God class (~402 lines) with 15+ methods.
- Rule duplication across IDE-specific files (`.cursor/`, `.claude/`, `.windsurf/`, etc.).
- SQLite in memory/workflow/saga has no WAL/lock.
- Dashboard lacks security headers, CSP, XSS sanitization.
- Several modules use broad `except Exception`.
- Missing dedicated tests for WorkflowRunner, SagaOrchestrator, McpClient, TelemetryCollector.

### Opportunities
- Adopt OPA/Rego for policies.
- Use `mcp-agent` or external MCP orchestrators.
- Move memory from vector-only to knowledge graph.
- Add SRE observability, Prometheus metrics, log rotation.
- Auto-generate IDE rules from `rules/vocabulary.md`.

### Threats
- Plugin execution without sandbox.
- AST policy evaluator allows `BinOp.Add` and could be extended by mistake.
- Dashboard defaults to no auth if token env is missing.
- `temp/` directory can break tools if not excluded.

---

## Issue Register

### P0 — Security
- [x] `runtime/plugin.py`: AST-based static sandbox blocks denylisted modules and dangerous calls before `exec_module`.
- [ ] `runtime/policy.py`: `_SafeEvaluator` still allows `BinOp.Add` (legitimate arithmetic; review if removal needed).
- [x] `dashboard/server.py`: added CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy.
- [x] `dashboard/index.html`: `escapeHtml` applied to dynamic data; SRI added for Chart.js CDN.
- [x] `dashboard/server.py`: token is now required; lazy-generated `state/dashboard.token` unless `AGENT_OS_DASHBOARD_ALLOW_NO_TOKEN=1`.
- [x] `aios_mcp/aizee_server.py`: singletons locked; stricter path validation and UNC/symlink checks.
- [x] `memory/store.py`: WAL, busy timeout, lock, and improved FTS5 sanitization.
- [x] `runtime/approval_cache.py`: fixed — `is_approved()` now uses `self._lock`.
- [x] `runtime/audit.py`: sensitive-key redaction added.

### P1 — Runtime Correctness
- [x] `runtime/mcp_client.py`: `_send()` now uses per-call reader thread with 30s timeout.
- [x] `runtime/mcp_client.py`: per-key `_SEND_LOCKS` added to serialize concurrent calls.
- [x] `runtime/workflow.py`: `_execute_step()` now catches exceptions around `act()` and `McpClient.call_tool()`.
- [x] `runtime/workflow.py` & `runtime/saga.py`: SQLite connections now use WAL, busy timeout, and locks.
- [x] `runtime/tech_stack.py`: `_clean_version` uses numeric regex extraction; parser failures logged.
- [ ] `runtime/persona.py`: mutable class-level `_DATA`; schema validation not yet added.
- [x] `runtime/kernel.py`: Pydantic validation exceptions caught specifically; other unexpected errors propagate.
- [x] `runtime/budget.py`: `_dirty` flag added; writes skipped when no changes.

### P2 — DevOps / Packaging
- [x] `Dockerfile`: pinned to `python:3.11.9-slim`; added `VOLUME` for state/brain/graphify-out.
- [x] `pyproject.toml`: added `bandit` and `pip-audit` to dev dependencies.
- [x] `install.sh`: `set -euo pipefail` and Python 3.10+ check.
- [x] `install.ps1`: Python 3.10+ check; backup before overwriting agent configs.
- [x] `.github/workflows/security.yml`: new workflow for `pip-audit` and `bandit`.
- [x] `.github/dependabot.yml` and `.github/CODEOWNERS` created.
- [ ] Branch protection / OIDC deployment not yet configured.

### P3 — Rules / Skills / Docs
- [x] `manifest.json`: version/date fixed; `cleanup`/`scm`, `data-migration`, `incident-response` triggers added.
- [x] `README.md`: badge counts updated to 73 skills and 27 workflows.
- [x] `workflows/README.md`: count corrected.
- [x] Rule duplication: VER-01, GIT-06, TEST-07 centralized in `rules/vocabulary.md` and references added across IDE files and `AGENTS.md`.
- [x] `workflows/code-quality.md` vs `skills/clean-code-guard.md`: standardized to 4 max arguments.
- [x] `[TRIGGER]` tags added to all workflow files (using manifest mapping).
- [x] Missing workflows: `18-data-migration.md` and `19-incident-response.md` created.
- [x] `scripts/validate-globals.py`: workflow count check added.
- [ ] `Memory.md`: auto-truncation not yet implemented.

### P5 — External Repository Research
- [x] `.ai/repos-study.md` created with an agent meta-prompt and a curated list of 30+ repositories.

### P4 — Tests
- [x] `runtime/tests/test_workflow.py`: added.
- [x] `runtime/tests/test_security.py`: added covering plugin sandbox, MCP path validation, audit redaction.
- [x] `test_saga.py`, `test_mcp_client.py`, `test_telemetry.py` already exist in `tests/runtime/`.
- [ ] `test_tech_stack.py`: exists but does not cover `_clean_version` edge cases.

---

## Recommended GitHub Repos to Study

### Agent OS / Governance
- RightNow-AI/openfang
- shackleai/orchestrator
- Justin0504/Sovereign-OS
- microsoft/agent-governance-toolkit
- preloop/preloop
- mnemopay/praetor
- nanny-run/nanny
- ViktorWelbers/paddock

### MCP Orchestration
- lastmile-ai/mcp-agent
- mrorigo/mcp-orchestrator
- musaceylan/OrchestrAI
- chrisnewell91/Meta-MCP-Server
- dufangshi/orchestration-mcp

### Policy / Rule Engines
- open-policy-agent/opa
- MAIF/arta
- poyao0705/guardian-angel
- JonSil89/gatehouse-policy-engine
- SemClone/ospac

### Coding Guardrails
- fjb040911/ai-rules
- yunbow/ai-dev-os
- nizos/probity
- stawils/coding-guardrails
- xianzuyang9-blip/agent-guardrails

### Memory / RAG / Knowledge Graph
- neo4j-labs/agent-memory
- PlateerLab/synaptic-memory
- mtrnix/metronix-memory
- XMUDeepLIT/MemGraphRAG
- MemMachine/MemMachine

---

## Next Steps

1. Run `python eval/harness.py` after each fix batch.
2. Update this file to mark issues done as they are fixed.
3. Do not run `git commit` or `git push` without explicit user approval.
