# UNIVERSAL EXECUTION WORKFLOW

Strictly follow this operational rhythm for EVERY user request:

## STEP 1: ROUTE & READ (CONTEXT GATHERING)
Before executing any task, you MUST silently read your foundational knowledge in this exact order:
1. **Base Context:** Read ALL rule files from `D:\server\.ai\rules\` — this includes environment, security, code quality, performance, git standards, and the principal architect persona.
2. **Workflow Route:** Identify the task type and read the corresponding protocol from `D:\server\.ai\workflows\`:
   - Planning/Architecture → `01-planning.md`
   - Writing/Modifying Code → `02-execution.md`
   - Debugging/Errors → `03-debugging.md`
   - Deploying/Releasing → `04-deployment.md`
   - Reviewing Code/PRs → `05-code-review.md`
3. **Tech-Stack Sync:** Scan the local project's `composer.json` or `package.json` and read the matching tech-stack files from `D:\server\.ai\tech-stack\`.

## STEP 2: THINK (INTERNAL REASONING)
Before responding, perform internal analysis:
1. Analyze the exact requirement and identify edge cases.
2. Check for security implications (OWASP Top 10), N+1 queries, and performance bottlenecks.
3. Plan your surgical code edits — identify exact files, line ranges, and dependencies.
4. Consider the architectural trade-offs of your approach.
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
3. **Build Check:** Ensure the project compiles/builds without errors.
4. **Regression Check:** Confirm existing functionality is not broken by the changes.
If verification fails, fix the issues before reporting completion. Never deliver unverified code.

## STEP 6: DOCUMENTATION SYNC
Upon completing a major milestone or fixing a critical bug:
1. Update the local project's `MEMORY.md` with a concise summary of accomplishments and architectural decisions.
2. If a global rule or tech-stack file was created/modified, append the change to `D:\server\.ai\CHANGELOG.md`.
3. Update any relevant inline documentation, README, or API docs affected by the changes.

## STEP 7: HANDOFF PROTOCOL
When ending a session or transferring context:
1. Summarize the current state — what was completed, what remains, and any known blockers.
2. Ensure `MEMORY.md` is up to date so the next session can resume without context loss.
3. If mid-task, clearly mark the stopping point and next steps in the task tracker.