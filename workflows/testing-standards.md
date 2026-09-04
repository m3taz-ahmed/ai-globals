[WORKFLOW] testing-standards
[OBJ] Testing Standards & Quality Assurance — two-tier strategy for ANY project under aiZee.
[TRIGGER] testing-standards
[RULES]
1. [REQ] Two-tier testing `[TEST-07]`:
   - FAST tier (during iteration): targeted tests only — the specific file/class/feature you touched. No full suites. ~5s max.
   - FULL tier (before declaring done): the project's complete test suite + coverage. Must pass green.
   - NEVER run the full suite on every change. NEVER skip the full suite before done.
2. [REQ] Tools `[TEST-04]`: Pest 3+ (isolated DB), Vitest + testing-library/react (userEvent). Playwright for E2E. pytest for Python.
3. [PROHIBIT] Mocks: NO live API requests (mock HTTP). Mock ONLY system boundaries. NEVER mock internal classes or state/DTOs.
4. [REQ] Coverage `[TEST-06]`: 95% total (aiZee Python). NO skipping tests without linked issue.
5. [REQ] Guards: Test behavior, not implementation. Merge duplicate setups into data-providers. Delete typo-tests. Regression tests are sacred.
6. [REQ] `[TEST-08]` Per-stack fast/full commands (see `workflows/testing-tiers.md`):
   - PHP/Laravel/Pest: `php artisan test --filter=<name>` (fast) / `php artisan test` (full)
   - JS/TS/Vitest: `npx vitest run <file>` (fast) / `npx vitest run` (full)
   - Python/pytest: `pytest <file> -q --no-cov` (fast) / `pytest --cov --cov-fail-under=95` (full)
   - Go: `go test <pkg> -short` (fast) / `go test ./... -race -cover` (full)
7. [REQ] `[TEST-09]` If the project has no test framework configured, write the FIRST test for the touched code before declaring done. Do not skip.
8. [REQ] `[TEST-10]` Mark slow tests (integration, E2E, model-loading, server-startup) with the framework's skip/标记 mechanism so fast tier stays fast.
