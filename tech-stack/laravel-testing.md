[TECH] laravel-testing
[OBJ] Laravel Testing Standards (Pest 3+ / PHPUnit 11+).
[RULES]
1. [REQ] Framework: Pest 3+ for new projects. PHPUnit 11+ for legacy. ⛔ NEVER mix Pest and PHPUnit in same suite.
2. [REQ] Two-Tier Testing `[TEST-07]`: FAST (targeted `--filter=` / `<file>`, ~5s) during iteration + FULL (complete suite + coverage 80%+) before done. ⛔ NEVER full suite on every change. ⛔ NEVER skip full suite before done.
3. [REQ] Factories: Every Model has a Factory. Seeders for reference data. ⛔ NEVER hardcoded IDs/dates in tests `[TEST-03]`.
4. [REQ] Helper Traits: `EntityProvider`, `UserRoleProvider`, `PermissionsProvider` for reusable test data setup (BookStack pattern). Compose in test classes via `use` trait.
5. [REQ] Custom Assertions: `assertActivityExists(ActivityType::X)`, `assertPermissionError()`, `assertModelMissing()`, `assertModelExists()` for domain-specific test readability (BookStack/Koel pattern).
6. [REQ] Helper Functions: `create_admin()`, `create_user()`, `create_vault()` as global test helpers in `tests/Concerns/` or `tests/helpers.php` (Koel pattern). Reduces test boilerplate.
7. [REQ] Security Tests: Dedicated security test suite — `AuthenticationHardeningTest`, `HtmlSanitizationTest`, `SvgUploadSanitizationTest`, `InstallerLockdownTest`, `PasswordResetStatusTest` (Krayin pattern). Separate `tests/Feature/Security/` folder.
8. [REQ] License/Feature Mocking: `FakePlusLicenseService`, `FakeNetwork` fakes for license-gated features (Koel pattern). Bind fakes in test setup. ⛔ NEVER hit real license/API servers in tests.
9. [REQ] Translation Consistency: Test that verifies all translation keys used in views exist in lang files (Bagisto `translation_tests.yml` pattern). Prevents missing translation keys in production.
10. [REQ] E2E: Playwright for admin + shop/user flows (Bagisto pattern). `admin_playwright_tests.yml` + `shop_playwright_tests.yml`. Separate from Pest/PHPUnit suite. Mark as slow `[TEST-10]`.
11. [REQ] Multi-DB: SQLite (default, in-memory) + MySQL + PostgreSQL test configs (`phpunit.{driver}.xml`). Run matrix in CI (Filament pattern). ⛔ NEVER assume single DB in tests.
12. [REQ] Parallel + Serial: `--parallel --exclude-group=serial` for default + `--group=serial` for tests that cannot parallelize (Filament pattern). Mark serial tests with `#[Group('serial')]`.
13. [REQ] Browser Testing: `pestphp/pest-plugin-browser` for Livewire/Filament interactions that need real browser (Filament pattern). Timeout config: `pest()->browser()->timeout(10000)`.
14. [REQ] API Structure Tests: `->assertJsonStructure(Resource::JSON_STRUCTURE)` + `->assertJsonStructure(Resource::PAGINATION_JSON_STRUCTURE)` for every API endpoint (Koel pattern). Structure constants on `JsonResource` classes.
15. [REQ] Cursor Pagination Tests: Traverse all supported sort columns without duplicates (Koel pattern). `while ($cursor !== null) { $r = $this->getAs(...); $allIds = array_merge(...); $cursor = $r->json('meta.next_cursor'); }` then `assertCount(N, array_unique($allIds))`.
16. [REQ] Bus Faking: `Bus::fake()` for job dispatch tests. Assert dispatched: `Bus::assertDispatched(JobClass::class)`. Assert not dispatched: `Bus::assertNotDispatched(JobClass::class)`.
17. [REQ] AAA Pattern `[TEST-02]`: Arrange-Act-Assert. One behavior per test `[TEST-02]`. Test method name describes behavior: `test_admin_can_create_post` or `it_can_paginate_songs_without_duplicates`.
18. [REQ] Coverage `[TEST-06]`: 80% logic, 90% API, 70% total. `--cov-fail-under=80` in CI. Coverage report: `--cov-report=html` + `--cov-report=term-missing`.
