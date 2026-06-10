---
name: test-driven-development
description: Use when implementing any feature/bugfix. Enforces Red-Green-Refactor.
---
# Test-Driven Development

**Mode**: Implementation.

## 🔴 The Iron Law
**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST.**

## 🧱 Red-Green-Refactor
1. **RED**: Write one minimal test showing what should happen.
2. **Verify RED**: Run test. Must FAIL for the right reason (not a typo).
3. **GREEN**: Write the simplest, most minimal code to pass the test. Do not over-engineer (YAGNI).
4. **Verify GREEN**: Run test. Must PASS.
5. **REFACTOR**: Clean up code/duplication without adding behavior. Keep tests passing.

**Red Flags (Delete code and start over if):**
- You wrote code before the test.
- Test passed immediately (proves nothing).
- You can't explain why the test failed.
- "I'll test after" or "It's too simple to test".
