# Phase 2: Execution & Development

1. **Iterative Delivery:** Build and detail one module at a time. Do not attempt to deliver an entire Monolith in one prompt.
2. **Surgical Edits (Diff Driven):** When modifying files, apply incremental diffs. Do NOT rewrite the entire file unless explicitly requested. Show exactly where code is added/removed.
3. **Design Patterns:** Favor Service Classes for business logic, Form Requests for validation, and Repositories/Actions where applicable to keep Controllers thin.
4. **Inline Documentation:** Complex logic MUST include concise, professional inline comments to aid future integration and maintenance. Document the "Why" in the comments.
5. **Checkpointing:** After completing a milestone, pause. Output a brief summary of what was achieved and await approval before moving to the next task.