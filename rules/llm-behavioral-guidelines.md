# LLM Behavioral Guidelines (Expanded Reference)
> [!NOTE]
> Trigger: behavioral review, onboarding, or code review. Deeper self-tests for `rules/core-behavioral-compact.md`.

## Think Before Coding `[BEH-01]`
- **Self-Test:** State assumptions explicitly. Present interpretations for ambiguity. Stop & ask if confused. Push back if simpler alternatives exist.

## Simplicity First `[BEH-02]`
- **Self-Test:** "Would a senior architect say this is overcomplicated?" If yes, simplify.
- **Guidance:** Solve today's problems, not tomorrow's. No abstractions/extensions without request.

## Surgical Changes `[BEH-03]`
- **Traceability:** "Can every changed line be traced directly to user's request?"
- **Guidance:** Match existing style strictly. Dead code cleanup applies *only* to code made dead by *your* change. ⛔ pre-existing dead code.

## Goal-Driven Execution `[BEH-04]`
- **Verification:** Vague tasks → Verifiable checklist. AAA pattern testing one behavior.
