---
name: writing-plans
description: Write structured plans for complex tasks.
---
[SKILL] writing-plans
[OBJ] Create step-by-step implementation plan before coding.
[RULES]
1. [PROHIBIT] No Placeholders: Never write "TBD" or "TODO". Provide EXACT code blocks.
2. [REQ] Granular Tasks: 1. Fail Test -> 2. Minimal Code -> 3. Pass Test -> 4. Commit.
3. [REQ] File Paths: Always include exact file paths to create/modify.
4. [REQ] Format: Use exact structure:
   # [Feature] Implementation Plan
   **Goal:** ...
   **Architecture:** ...
   ### Task 1: [Component]
   **Files:** ...
   - [ ] Step 1: Write failing test (code block)
   - [ ] Step 2: Minimal implementation (code block)
5. [REQ] Plan is executable by a stranger: each task self-contained — what changes, in which file, what code, what test proves it, what "done" looks like. Ambiguity in a plan becomes thrash in implementation.
6. [REQ] Right-size decomposition: tasks split at verifiable boundaries (a test that can fail, a module that compiles); too-big tasks hide risk, too-small tasks drown in ceremony. Sweet spot: one commit-sized unit of verifiable change.
7. [REQ] Ordering by risk + dependency: hardest/uncertain piece first (kills bad plans early); dependencies sequenced (schema before service, interface before callers); parallelizable tasks marked as such.
8. [REQ] Failure paths planned: every task that can go wrong gets a rollback/abort note; risky steps get a spike/validation task ahead of the build task — don't discover the approach is wrong at step 9.
9. [REQ] Acceptance criteria per task: observable, binary ("endpoint returns 201 with id", "test X passes"), not "works correctly". The implementer (or subagent) must be able to verify without asking.
10. [REQ] Scope containment: plan covers ONLY the requested change — refactors, drive-bys, and cleanups get separate plans. Every task traces back to the goal; plan audit cuts anything that doesn't.
11. [REQ] Assumptions explicit: list version assumptions, integration contracts, open questions — with the resolution for each BEFORE task 1 (or a task 0 that resolves it).
12. [PROHIBIT] Plans written in present-tense narration ("we will..."), tasks without testable completion, code blocks marked "similar to existing", or plans that skip the verification step at the end (how do we prove the whole thing works?).
