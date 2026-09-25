[FILE] task-contract
[OBJ] Enforced decompose → verify → review contract for non-trivial work.
[RULES]
1. [REQ] `[TASK-01]` Classify First: Every work prompt gets a recorded classification — `trivial | standard | complex` + a justification. Use `aizee task classify --prompt "..." --level X --reason "..."`. No silent skips; the AI must explain the call. When in doubt, classify UP.
2. [REQ] `[TASK-02]` Decompose Non-Trivial: `standard`/`complex` work requires `.task/plan.json` via `aizee task decompose` BEFORE any implementation edit. Each task: kebab id, title, `depends_on` (acyclic), `files` (declared scope), `acceptance` (checkable), `produces` (handoff contract), `risk`.
3. [REQ] `[TASK-03]` One Active Task: `aizee task start <id>` only when deps are `done` and no task is active. Work outside the active task's declared scope → `aizee task amend` first.
4. [REQ] `[TASK-04]` Evidence Before Done: `aizee task verify <id> --evidence "..."` — test output, command result (`--run` executes `verify_cmd`), or diff summary. A bare claim is not evidence. Then `aizee task complete <id>`.
5. [REQ] `[TASK-05]` Final Review: `aizee task finish` closes the plan and emits the mandatory checklist — FULL test tier, diff-vs-scope review, acceptance conformance. Plan closed ≠ work done until the checklist passes.
6. [REQ] `[TASK-06]` Amend Don't Drift: mid-flight plan changes go through `aizee task amend --ops ... --reason "..."`. Amendments are logged; silent scope drift is a violation.
7. [PROHIBIT] No `complete` without `verify`. No `finish` with pending tasks (complete, block, or amend). No second active plan (`finish`/`abandon` first).
8. [REQ] Trivial Exemption: a prompt MAY skip the plan only after a recorded `trivial` classification with a real reason (typo, rename, comment, single localized fix). Record via `aizee task classify`.
9. [CMD] Strict mode: `AIZEE_TASK_STRICT=1` makes out-of-scope edits raise `SCOPE_VIOLATION` instead of warn.
10. [CMD] Hook surface: `aizee hook inject` prints the active contract (progress, active task, scope); `afterFileEdit` observe emits scope warnings.
