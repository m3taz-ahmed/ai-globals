# Phase 3: Advanced Debugging & RCA

1. **Format Enforcement:** You must process issues based on `[Error Message + Relevant Code + Logs]`. If the user provides an error without context, ask for the code and logs first.
2. **Root Cause Analysis (RCA):** Do NOT guess. Trace the exact logical failure across the Stack, Database, or Server configuration.
3. **The "No Band-Aids" Rule:** Apply permanent architectural fixes. Never use `@` in PHP to suppress errors, never disable strict types to bypass a bug, and never ignore TypeScript/Node.js warnings.
4. **Verification & Explanation:** Clearly explain what caused the error at a system level, how the fix addresses the root cause directly, and how to prevent it in the future.