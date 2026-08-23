# `workflows/` — Execution Protocols

Each file here activates when the AI detects a specific task type. Counts and the routing table below are maintained automatically by [`scripts/sync_docs.py`](../scripts/sync_docs.py).

## Numbered Workflows (Trigger-Based)

This directory contains **50** `.md` files: **36** numbered trigger-based workflows (`00`-`35`) plus standards protocols and reference files.

| Trigger / Task Type | Workflow File | When to Use |
|---|---|---|
| /prompt | `00-prompt-architecting.md` | Prompt generation protocol. |
| architecture | `01-planning.md` | Feature planning and architecture. |
| implementation | `02-execution.md` | Code generation and development. |
| bug | `03-debugging.md` | Advanced debugging and RCA. |
| deploy | `04-deployment.md` | Deployment and Release protocol. |
| code review | `05-code-review.md` | Code Review Specialist protocol. |
| maintenance | `06-maintenance.md` | System Maintenance & Global Optimization. |
| security audit | `07-security-audit.md` | Security review and infrastructure hardening. |
| onboarding | `08-onboarding.md` | Project Onboarding & AI Architect Initialization. |
| tech discovery | `09-discovery.md` | AI Discovery Workflow for unknown tech stacks. |
| multi-agent | `10-saga-reconciliation.md` | Multi-Agent State Resilience and Conflict Resolution. |
| `/audit-core` | `11-audit-core.md` | Elite backend, logic, and security bug-hunt for active repo. |
| `/audit-ui` | `12-audit-ui.md` | Elite UI/UX, aesthetics, and visual performance teardown. |
| `/audit-perf` | `13-audit-perf.md` | Extreme speed, database, and caching optimization analysis. |
| `/ponytail-review` | `14-ponytail-review.md` | Ruthless simplification — delete over-engineering, replace with minimal native code. |
| /page-builder | `15-page-builder-setup.md` | Scaffold a section-based landing/page builder in a Laravel + Filament project. |
| cleanup | `16-cleanup-and-scm.md` | Remove temporary and scratch files, review source control, and stage only relevant change… |
| memory sync | `17-memory-sync.md` | Compress session learnings into continuous context. |
| data-migration | `18-data-migration.md` | Database migrations, schema changes, and data transformation. |
| incident-response | `19-incident-response.md` | Production incidents, outages, and emergency hotfixes. |
| freelance | `20-freelance-pipeline.md` | End-to-end freelance job-to-contract pipeline: profile, search, score, proposal, approval… |
| 21-spec-driven | `21-spec-driven.md` | Structured 4-phase development process: **Specify → Plan → Tasks → Implement**. |
| 22-spec-analyze | `22-spec-analyze.md` | Non-destructive cross-artifact consistency analysis across `spec.md`, `plan.md`, and `tas… |
| 23-spec-converge | `23-spec-converge.md` | Assess the codebase against a feature's spec/plan/tasks to identify remaining work. Class… |
| /laravel-architecture | `24-laravel-architecture-setup.md` | Scaffold Laravel architecture patterns (Service Layer / Repository / DTO / Actions / DDD)… |
| /filament-plugin | `25-filament-plugin-development.md` | Develop custom Filament plugins implementing the Plugin interface with register/boot life… |
| /api-versioning | `26-laravel-api-versioning.md` | Setup header-based API versioning in Laravel (Koel pattern) with versioned route files an… |
| /nativephp | `27-nativephp-app-development.md` | Full lifecycle for building native desktop/mobile apps with NativePHP (Laravel). Detect t… |
| seo audit | `28-seo-audit.md` | Comprehensive SEO audit protocol for any website — technical, content, schema, GEO/AEO, p… |
| filament ai | `29-filament-ai-workflow.md` | AI-assisted Filament development using Boost + Compass + FilaCheck pipeline. |
| generate skill | `30-skill-generation.md` | Convert books, documents, RFCs, wikis, and PDFs into structured aiZee skills. Extract fra… |
| draft and review | `31-drafter-reviewer.md` | Two-agent pipeline for content generation with adversarial review. The drafter produces a… |
| mobile bootstrap | `32-mobile-app-bootstrap.md` | Bootstrap a production-grade cross-platform mobile app — Flutter or React Native/Expo — w… |
| multi-tool sync | `33-multi-tool-sync.md` | Materialize aiZee's single source of truth into every AI coding tool's native format. Eli… |
| agent gateway | `34-agent-gateway-audit.md` | Audit all LLM/MCP traffic passing through the agent gateway. Every request and response i… |
| reliability eval | `35-reliability-eval.md` | Score AI coding agents with reliability@k + security-adjusted reliability@k. Replace the… |

## Standards & Reference Files

| File | Purpose |
|---|---|
| `git-standards.md` | Git branching, commits, PR rules |
| `ci-cd-standards.md` | CI/CD pipeline and deployment gates |
| `testing-standards.md` | Test coverage, frameworks, TDD protocol |
| `security-standards.md` | OWASP, RBAC, threat modeling |
| `performance-standards.md` | Query budgets, caching, profiling |
| `observability-standards.md` | Logging, tracing, health checks |
| `code-quality.md` | SOLID, DRY, complexity gates |
| `devops-standards.md` | Infrastructure, containers, IaC |
| `cheat-sheet.md` | Quick command reference |
| `commands-reference.md` | Full CLI/tooling reference |
| `monthly-maintenance.md` | Monthly audit protocol |
| `update-me.md` | AI self-update protocol |

## Execution Model

Workflows follow the global **7-Step Execution Loop** in `global-workflow.md`:

```
Step 1: ROUTE & READ  → Load context layers (0 → 1 → 2 → 3)
Step 2: THINK         → Internal reasoning, anti-pattern check
Step 3: GOLDEN RULE   → Clarify if ambiguous (≥80% clear = proceed)
Step 4: EXECUTE       → Deliver with verifiable success criteria
Step 5: VERIFY        → Run tests, static analysis, formatting
Step 6: DOCS SYNC     → Update Memory.md and CHANGELOG.md
Step 7: HANDOFF       → Summarize state for next agent/session
```

## Machine-Readable Routing

See `manifest.json` at repo root for the trigger→workflow map used by automated tools.

## Adding a New Workflow

1. Name the file `{NN}-{description}.md` (continue the numbering sequence)
2. Add it to the routing table in `global-workflow.md` Step 1 Layer 3
3. Add it to this README and to `manifest.json`
4. Log it in `CHANGELOG.md`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full process.
