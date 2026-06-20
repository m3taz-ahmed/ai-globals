[WORKFLOW] testing-standards
[OBJ] Testing Standards & Quality Assurance.
[RULES]
1. [REQ] Tools `[TEST-04]`: Pest 3+ (isolated DB), Vitest + testing-library/react (userEvent). Playwright for E2E.
2. [PROHIBIT] Mocks: NO live API requests (mock HTTP). Mock ONLY system boundaries. NEVER mock internal classes or state/DTOs.
3. [REQ] Coverage `[TEST-06]`: 80% logic, 90% APIs. NO skipping tests without linked issue.
4. [REQ] Guards: Test behavior, not implementation. Merge duplicate setups into data-providers. Delete typo-tests. Regression tests are sacred.
