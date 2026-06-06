# GLOBAL WORKFLOW SYNCHRONIZATION
> [!IMPORTANT]
> **Discovery:** Scan `workflows/` at start of any task as primary execution blueprint.

## STEP 1: ROUTE & READ (Layered Context Loading)
Load context in order (silently):
- **Layer 0 — ALWAYS (Behavioral Core):**
  - `rules/core-behavioral-compact.md` — Non-negotiable behavioral core (< 50 lines)
  - `global-roles.md` — Architecture, gates, communication
- **Layer 1 — ALWAYS (Structural Rules):**
  - `./.ai/active-context.md` — Local project persistent memory context
  - `rules/vocabulary.md` — Central symbolic rules dictionary
  - `rules/anti-patterns.md` — Negative constraints
  - `useful-repos.md` — Tools & methodologies registry
- **Layer 2 — ON-DEMAND (Domain Rules):** (Read ONLY if relevant)
  - Behavioral review → `rules/llm-behavioral-guidelines.md`
  - Security → `rules/security-standards.md`
  - External APIs → `rules/api-integration-standards.md`
  - Observability/Logging → `rules/observability-standards.md`
  - Performance → `rules/performance-standards.md`
  - Git/PR → `rules/git-standards.md`
  - SaaS/Multi-tenancy → `rules/saas-standards.md`
  - Architecture → `rules/principal-architect.md`
  - Code Quality → `rules/code-quality.md`
  - Windows Env → `rules/environment-windows.md`
- **Layer 3 — ON-DEMAND (Workflows & Tech-Stack):**
  - **Workflow Route:** Run matching file in `workflows/`:
    - Prompt Architecting → `00-prompt-architecting.md` (Trigger: `/prompt`)
    - Planning → `01-planning.md`
    - Execution → `02-execution.md`
    - Debugging → `03-debugging.md`
    - Deployment → `04-deployment.md`
    - Review → `05-code-review.md`
    - Maintenance → `06-maintenance.md`
    - Security Audit → `07-security-audit.md`
    - Onboarding → `08-onboarding.md`
  - **Tech-Stack Lazy Loading:** Read ONLY matching files from `./tech-stack/` based on `package.json`/`composer.json`. Ignore spec files marked `[!SPECULATIVE]` unless matching pre-release stack.

## STEP 2: THINK (Internal Reasoning)
Prior to responding:
1. Identify edge cases & requirements.
2. Security (OWASP), N+1, performance checks.
3. Validate approach doesn't violate `rules/anti-patterns.md` / `[SEC-xx]`.
4. Webhooks/APIs follow `rules/api-integration-standards.md` / `[API-xx]`.
5. Subagents follow Saga handshake (`workflows/10-saga-reconciliation.md`).
6. Plan surgical diffs (files, line ranges).

## STEP 3: THE GOLDEN RULE (Ask First)
No blind large-code generation. Stop & ask if requirements are ambiguous (<80% clear).

## STEP 4: EXECUTE & DELIVER
- **Success Criteria:** Write verifiable checks first:
  `[Step] → verify: [check]`
- **Rules:** Clean iterative edits, surgical diffs, local skills delegation (`subagent-driven-development` and `tdd-workflows`), reference `EXAMPLES.md` for patterns.

## STEP 5: VERIFY & FORMAT
1. Run target test suite (e.g. `php artisan test --filter`, `npm test`).
2. Run static analysis/linters.
3. Keep technical terms in English inside translation output.

## STEP 6: DOCUMENTATION & HANDOFF (AUTO-TRIGGER)
> [!IMPORTANT]
> You must proactively execute this step automatically whenever you complete a major task, logical milestone, or right before completing the user's core request. Do NOT wait for the user to explicitly ask you to "save the session".

1. Run `workflows/09-memory-sync.md` to compress session context into `./.ai/active-context.md`.
2. Update global `MEMORY.md` (for architectural changes) and `./CHANGELOG.md` (for rule changes).
3. Summarize remaining tasks, blockers, and state for next session.
