# `workflows/` — Execution Protocols

This directory contains **28 execution protocol files** (15 numbered workflows + 13 standards/reference files). Each activates when the AI detects a specific task type.

## Numbered Workflows (Trigger-Based)

| Trigger / Task Type | Workflow File | When to Use |
|---|---|---|
| `/prompt` command | `00-prompt-architecting.md` | Refining vague requirements before writing any code |
| Architecture / planning | `01-planning.md` | New features, system design, risk assessment |
| Writing / modifying code | `02-execution.md` | Implementation, refactoring, iterative delivery |
| Bugs / errors | `03-debugging.md` | Error diagnosis, root cause analysis, post-mortem |
| Releases / deploys | `04-deployment.md` | Deployment, rollback procedures, health checks |
| Code review / PRs | `05-code-review.md` | Quality, security, performance review |
| System maintenance | `06-maintenance.md` | Monthly deep-scan, tech debt, rule updates |
| Security hardening | `07-security-audit.md` | Security audit, OWASP scan, hardening protocol |
| New project setup | `08-onboarding.md` | AI initialization, baseline audit, stack detection |
| Tech discovery / research | `09-discovery.md` | Research and integration of bleeding-edge stacks |
| Multi-agent execution | `10-saga-reconciliation.md` | Saga State Machine tracking for parallel agents |
| Backend/logic/security audit | `11-audit-core.md` | Deep audit of backend, logic, and security bugs |
| UI/UX/visual audit | `12-audit-ui.md` | Teardown of UI, UX, aesthetics, and visual performance |
| Performance/caching audit | `13-audit-perf.md` | Speed, database, and caching optimization analysis |
| Simplification review | `14-ponytail-review.md` | Delete over-engineering; replace with minimal native code |

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
| `09-memory-sync.md` | State handoff and memory sync on milestones |

## Execution Model

Workflows follow the global **7-Step Execution Loop** in `global-workflow.md`:

```
Step 1: ROUTE & READ  → Load context layers (0 → 1 → 2 → 3)
Step 2: THINK         → Internal reasoning, anti-pattern check
Step 3: GOLDEN RULE   → Clarify if ambiguous (≥80% clear = proceed)
Step 4: EXECUTE       → Deliver with verifiable success criteria
Step 5: VERIFY        → Run tests, static analysis, formatting
Step 6: DOCS SYNC     → Update state/MEMORY.md and state/CHANGELOG.md
Step 7: HANDOFF       → Summarize state for next agent/session
```

## Machine-Readable Routing

See `manifest.json` at repo root for the trigger→workflow map used by automated tools.

## Adding a New Workflow

1. Name the file `{NN}-{description}.md` (continue the numbering sequence)
2. Add it to the routing table in `global-workflow.md` Step 1 Layer 3
3. Add it to this README and to `manifest.json`
4. Log it in `state/CHANGELOG.md`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full process.
