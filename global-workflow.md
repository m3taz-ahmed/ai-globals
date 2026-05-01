# Master Global Workflow
> [!NOTE]
> Update `D:\server\.ai\` in the paths below if your repository is located elsewhere.

## STEP 1: ROUTE & READ (CONTEXT GATHERING)
Before executing any task, you MUST silently read your foundational knowledge in this exact order:

1. **Initialize AI Architect:** Start immediately by reading the operating protocols from the absolute path `D:\server\.ai\`. Do not rely on any prior assumptions.
2. **Base Context:** Read ALL rule files from `D:\server\.ai\rules\` — this includes environment, security, code quality, performance, git standards, anti-patterns, API integration standards, observability standards, and the principal architect persona.
3. **Workflow Route:** Identify the task type and read the corresponding protocol from `D:\server\.ai\workflows\`:
   - Planning/Architecture → `01-planning.md`
   - Writing/Modifying Code → `02-execution.md`
   - Debugging/Errors → `03-debugging.md`
   - Deploying/Releasing → `04-deployment.md`
   - Reviewing Code/PRs → `05-code-review.md`

4. **Tech-Stack Sync:** DYNAMIC TECH-STACK (LAZY LOADING)
Scan the local workspace's `composer.json` or `package.json` to detect the exact stack.
**Strict Lazy Load:** SILENTLY READ ONLY the specific `.md` files from `D:\server\.ai\tech-stack\` that match the detected stack or the user's explicit request. 
**Do NOT** read unrelated tech-stack files. (e.g., If working on a PHP/Laravel task, ignore Node.js or React files unless specifically instructed).

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
When producing code:
1. Follow the active workflow protocol (planning/execution/debugging/deployment/review).
2. Deliver iteratively — one module or logical unit at a time.
3. Include all necessary components (migrations, models, services, tests).
4. Apply surgical diffs — never rewrite entire files unless explicitly requested.

## STEP 5: VERIFY & VALIDATE
After making any changes, you MUST verify before reporting completion:
1. **Tests:** Run the project's test suite (`php artisan test`, `npm test`, etc.) and confirm all tests pass.
2. **Static Analysis:** Run linters/analyzers if configured (`phpstan`, `eslint`, etc.).
## STEP 6: VERIFICATION & FORMATTING
1. **Verification:** Run tests and build checks. Never deliver unverified code.
2. **Formatting:** If responding in Arabic, strictly follow the `global-roles.md` formatting rules for English terms (use backticks) to ensure correct text alignment.

## STEP 7: DOCUMENTATION SYNC
1. Update the local project's `MEMORY.md` with accomplishments and decisions.
2. If a global rule was modified, update `D:\server\.ai\CHANGELOG.md`.
3. Update relevant inline docs, README, or API docs.

## STEP 8: HANDOFF PROTOCOL
1. Summarize state, remaining tasks, and blockers.
2. Ensure `MEMORY.md` is current for the next agent.