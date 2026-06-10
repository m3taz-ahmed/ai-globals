---
name: test-guard
description: Review generated test code against universal testing rules. Prevent AI-generated test bloat, mock-heavy tests, and testing framework behavior.
---
# test-guard

**Mode**: Run before presenting/committing tests.

## 🔴 Core Directives
1. **Test behavior, not implementation**: Assert return values/state changes, not that an internal helper was called.
2. **Mocks only at system boundaries**: Mock Network, DB, FS, LLMs. NEVER mock internal classes or state objects.
3. **One scenario per test**: Merge duplicate setups using data-providers (`@pytest.mark.parametrize`, `test.each`, etc).
4. **Justify Existence**: Delete tests catching typos or testing trivial logic (e.g., framework features like "Router returns 404").
5. **Name for Scenario**: Use `test_<scenario>_<expected_outcome>`.
6. **No state object mocking**: Use real DTOs/Entities. Mocking state hides real validation bugs.
7. **Real Infrastructure**: Tests for DB queries MUST use a real test database, not a mocked connection.

**Severity**:
- **Must fix**: Testing implementation, unjustified mocks, mocking state.
- **Should fix**: Bloat, bad names, testing the framework.

**Checklist**:
- Does this test verify my logic or the framework's logic?
- Are we mocking internal helpers? (If yes, fix).
- Can multiple tests be merged into a data provider?
