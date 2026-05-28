# Phase 2: Execution & Development
> [!NOTE]
> Trigger: Writing or modifying code.

## Execution Rules
- **Iterative Delivery:** Build/deliver one module at a time. ⛔ monolithic dumps.
- **Surgical Edits:** Apply incremental diffs. ⛔ rewrite entire files. Use placeholders (`// ... existing code ...`).
- **Patterns:** Services for logic, Form Requests for validation, Repositories/Actions where applicable. Thin controllers.
- **Inline Docs:** Professional inline comments documenting the "Why", not the "What" for complex logic.
- **TDD Workflow:** Write tests concurrently. Deliver: Migration → Model → Service → Controller → Test.
- **Self-Check Checklist:** Validate Types, FormRequest, Security (no raw SQL/mass-assign/exposed secrets), Performance (no N+1), Errors (try/catch), Tests, and Docs.
- **Checkpointing:** Pause after milestones. Await approval before starting the next.
- **Token Efficiency:** ⛔ output unchanged code. Keep conversations terse to save context window.
- **Delegation:** Call available local `<skills>` (e.g. `tdd-workflows`, `subagent-driven-development`) for complex tasks.
