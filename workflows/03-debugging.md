# Phase 3: Advanced Debugging & RCA

## 1. FORMAT ENFORCEMENT
You must process issues based on `[Error Message + Relevant Code + Logs]`. If the user provides an error without context, ask for the code and logs first.

## 2. ROOT CAUSE ANALYSIS (RCA)
Do NOT guess. Trace the exact logical failure across the Stack, Database, or Server configuration.

## 3. THE "NO BAND-AIDS" RULE
Apply permanent architectural fixes. Never use `@` in PHP to suppress errors, never disable strict types to bypass a bug, and never ignore TypeScript/Node.js warnings.

## 4. STRUCTURED DEBUGGING PROTOCOL
When facing a non-obvious bug, follow this systematic approach:
1. **Reproduce:** Create a minimal reproduction case. Define exact steps to trigger the bug.
2. **Isolate:** Use binary search â€” disable half the suspected code, narrow down which half causes the issue, repeat.
3. **Hypothesize:** Form a specific, testable hypothesis about the cause before changing code.
4. **Verify:** Apply the fix and verify it resolves the exact reproduction case.
5. **Regression:** Confirm the fix doesn't break existing functionality by running the full test suite.

## 5. POST-MORTEM TEMPLATE
For critical bugs (production downtime, data issues), document:
- **What happened:** Exact symptoms and impact (users affected, duration).
- **Root cause:** The specific technical failure and why it wasn't caught.
- **Fix applied:** What was changed and why.
- **Prevention:** What process/test/guard will prevent recurrence.
- **Timeline:** When discovered â†’ diagnosed â†’ fixed â†’ deployed.
Store post-mortems in the project's `MEMORY.md` under a `## Post-Mortems` section.

## 6. VERIFICATION & EXPLANATION
Clearly explain what caused the error at a system level, how the fix addresses the root cause directly, and how to prevent it in the future.