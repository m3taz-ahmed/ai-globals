---
name: writing-plans
description: Use when you have an approved spec, before touching code, to create a step-by-step implementation plan.
---
# Writing Plans

**Mode**: Run after brainstorming/spec approval.

## 🔴 Rules
Write a highly detailed, task-by-task plan. Assume the executor has zero context and questionable taste.

**Bite-sized tasks**:
- Write failing test
- Run test (verify fail)
- Write minimal code
- Run test (verify pass)
- Commit

**No Placeholders**:
- NEVER write "TBD", "TODO", "add error handling". Provide the actual code blocks or exact expectations.
- Always include exact file paths to create/modify/test.

## 🧱 Output Format
```markdown
# [Feature] Implementation Plan
**Goal:** ...
**Architecture:** ...

### Task 1: [Component]
**Files:** Create: `x.js`, Modify: `y.js`
- [ ] Step 1: Write failing test (code block)
- [ ] Step 2: Run test to fail
- [ ] Step 3: Write minimal implementation (code block)
- [ ] Step 4: Verify test passes
- [ ] Step 5: Commit
```

**Next Step**: Ask user to execute via `subagent-driven-development` or inline execution.
