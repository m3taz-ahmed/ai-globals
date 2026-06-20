[SKILL] test-guard
[OBJ] Prevent AI test bloat and invalid mocking.
[RULES]
1. [REQ] Behavior: Test return values/state, not internal helper logic.
2. [REQ] Mocks: ONLY mock Network, DB, FS, LLM boundaries. NEVER mock internal classes or state.
3. [REQ] Efficiency: Merge duplicate setups into data-providers/parametrize. Delete trivial tests.
4. [REQ] DB: Queries MUST use a real test database.
5. [REQ] Names: `test_<scenario>_<expected_outcome>`.
