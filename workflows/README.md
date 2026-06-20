# `workflows/` — Execution Protocols

This directory contains **11 trigger-based workflow protocols**. Each workflow activates when the AI detects a specific task type, providing a structured, expert execution path.

## Routing Map

The AI selects the correct workflow automatically based on the task context:

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
| Tech discovery / research | `09-discovery.md` | Research and integration of unknown or bleeding-edge tech stacks |
| Multi-agent execution | `10-saga-reconciliation.md` | Saga State Machine tracking and handshake protocols for parallel execution |

## Execution Model

Workflows follow the global **7-Step Execution Loop** defined in `global-workflow.md`:

```
Step 1: ROUTE & READ  → Load context layers (0 → 1 → 2 → 3)
Step 2: THINK         → Internal reasoning, anti-pattern check
Step 3: GOLDEN RULE   → Clarify if ambiguous (≥80% clear = proceed)
Step 4: EXECUTE       → Deliver with verifiable success criteria
Step 5: VERIFY        → Run tests, static analysis, formatting
Step 6: DOCS SYNC     → Update state/MEMORY.md and state/CHANGELOG.md
Step 7: HANDOFF       → Summarize state for next agent/session
```

## Adding a New Workflow

1. Name the file `{NN}-{description}.md` (continue the numbering sequence)
2. Add it to the routing table in `global-workflow.md` Step 1 Layer 3
3. Add it to the System Map in `README.md`
4. Log it in `state/CHANGELOG.md`

See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full process.
