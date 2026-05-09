# GLOBAL WORKFLOW SYNCHRONIZATION
> [!IMPORTANT]
> **Workflow Discovery:** Every execution plan must start by scanning the `workflows/` directory in this Global AI Operating System. Use these as the primary blueprint for task execution.

## STEP 1: ROUTE & READ (LAYERED CONTEXT LOADING)
Before executing any task, you MUST silently load context in **layers** — from lightweight behavioral core to domain-specific depth:

### Layer 0 — ALWAYS (Behavioral Core)
Read FIRST, on every task, no exceptions:
- `rules/core-behavioral-compact.md` — The 4 non-negotiable behavioral principles (< 50 lines)
- `global-roles.md` — Architectural identity, quality gates, communication protocol

### Layer 1 — ALWAYS (Structural Rules)
Read immediately after Layer 0:
- `rules/anti-patterns.md` — Hard-stop negative constraints

### Layer 2 — ON-DEMAND (Domain Rules)
Read ONLY when the task involves the relevant domain:
- Behavioral review/onboarding → `rules/llm-behavioral-guidelines.md`
- Security-related → `rules/security-standards.md`
- External APIs → `rules/api-integration-standards.md`
- Monitoring/Logging → `rules/observability-standards.md`
- Performance work → `rules/performance-standards.md`
- Git/PR work → `rules/git-standards.md`
- SaaS/Multi-tenancy → `rules/saas-standards.md`
- Architecture review → `rules/principal-architect.md`
- Code quality audit → `rules/code-quality.md`
- Windows environment → `rules/environment-windows.md`

### Layer 3 — ON-DEMAND (Workflow + Tech-Stack)
1. **Workflow Route:** Identify the task type and read the corresponding protocol:
   - Prompt Architecting → `00-prompt-architecting.md` (Trigger: `/prompt`)
   - Planning/Architecture → `01-planning.md`
   - Writing/Modifying Code → `02-execution.md`
   - Debugging/Errors → `03-debugging.md`
   - Deploying/Releasing → `04-deployment.md`
   - Reviewing Code/PRs → `05-code-review.md`
   - System Maintenance/Audit → `06-maintenance.md`
   - Security Audit/Hardening → `07-security-audit.md`
- Project Onboarding → `08-onboarding.md`

  2. **Tech-Stack Sync (Lazy Loading):**
Scan the local workspace's `composer.json` or `package.json` to detect the exact stack.
**Strict Lazy Load:** SILENTLY READ ONLY the specific `.md` files from `./tech-stack/` that match the detected stack or the user's explicit request.
**Do NOT** read unrelated tech-stack files.
> **Speculative Files:** Files marked `[!SPECULATIVE]` (e.g., `php-8-5.md`, `laravel-13.md`, `filament-5.md`, `mysql-9-7.md`) should only be loaded when explicitly working with pre-release versions. Skip them by default to avoid applying unconfirmed standards.

## STEP 2: THINK (INTERNAL REASONING)
Before responding, perform internal analysis:
1. Analyze the exact requirement and identify edge cases.
2. Check for security implications (OWASP Top 10), N+1 queries, and performance bottlenecks.
3. **Anti-Pattern Cross-Check:** Verify your planned approach does NOT violate any constraint in `rules/anti-patterns.md`. If it does, redesign before proceeding.
4. **External Integration Check:** If the task involves external APIs or webhooks, apply `rules/api-integration-standards.md` patterns (retry, circuit breaker, error handling).
5. Plan your surgical code edits — identify exact files, line ranges, and dependencies.
6. Consider the architectural trade-offs of your approach.
Only after completing this reasoning can you provide the final response.

## STEP 3: THE GOLDEN RULE (ASK FIRST)
Do NOT generate massive blocks of code blindly. If requirements are ambiguous, or if multiple architectural paths exist, ask clarifying questions first. Reference the Communication Protocol in `global-roles.md` §5 for the ask-vs-act threshold.

## STEP 4: EXECUTE & DELIVER

### Success Criteria Framework (Mandatory)
Before writing ANY code, define verifiable success criteria:
```
1. [Step] → verify: [specific check]
2. [Step] → verify: [specific check]
3. [Step] → verify: [specific check]
```
Transform vague tasks into testable goals:
- "Fix X" → "Write a test that reproduces X, then make it pass"
- "Add Y" → "Write tests for Y's expected behavior, then implement"
- "Refactor Z" → "Ensure tests pass before AND after refactoring"

### Execution Rules
When producing code:
1. Follow the active workflow protocol (planning/execution/debugging/deployment/review).
2. Deliver iteratively — one module or logical unit at a time.
3. Include all necessary components (migrations, models, services, tests).
4. Apply surgical diffs — never rewrite entire files unless explicitly requested.
5. Refer to `EXAMPLES.md` for correct patterns when in doubt about LLM behavioral pitfalls.

## STEP 5: VERIFY, VALIDATE & FORMAT
After making any changes, you MUST verify before reporting completion:
1. **Tests:** Run the project's test suite (`php artisan test`, `npm test`, etc.) and confirm all tests pass.
2. **Static Analysis:** Run linters/analyzers if configured (`phpstan`, `eslint`, etc.). Never deliver unverified code.
3. **Formatting:** Use the same language as the user. Technical terms remain in English. No additional strict formatting is required for English terms within Arabic text.

## STEP 6: DOCUMENTATION SYNC
1. Update the local project's `MEMORY.md` with accomplishments and decisions.
2. If a global rule was modified, update `./CHANGELOG.md`.
3. Update relevant inline docs, README, or API docs.

## STEP 7: HANDOFF PROTOCOL
1. Summarize state, remaining tasks, and blockers.
2. Ensure `MEMORY.md` is current for the next agent.