# Testing Standards & Quality Assurance

> [!NOTE]
> **TRIGGER:** LOAD ON writing tests, CI/CD pipeline setup, QA workflows, test debugging.
> **SCOPE:** Pest 3+ (Laravel), Vitest (React), Playwright (E2E), TDD, Coverage Enforcement.

## 1. Test Pyramid & Frameworks

- Adhere to the **Test Pyramid**: many Unit tests (70%), fewer Integration tests (20%), and critical E2E tests (10%).
- Use **Pest 3+** for all Laravel 12/13 backend testing (Feature + Unit). Use Pest's expressive, functional syntax.
- Use **Vitest** for Next.js/React component and utility testing. Configure `vitest.config.ts` with `environment: 'jsdom'` for DOM-dependent components.
- Use **Playwright** for critical end-to-end user journeys (e.g., checkout, signup, multi-tenant switching). Do not use Playwright for logic that can be tested at lower pyramid levels.

## 2. Backend Testing (Pest / Laravel 12/13)

- Use Database Factories extensively to generate realistic test data. Define factory states for common scenarios (e.g., `UserFactory::new()->premium()`).
- Ensure test isolation; tests must not depend on the order of execution or shared database state (use `RefreshDatabase`).
- Mock external services (Stripe, SES, third-party APIs) using Laravel's `Http::fake()` or mock objects to prevent network dependencies in CI.
- Test multi-tenant scenarios explicitly by asserting data isolation between tenant contexts. Create dedicated `TenantIsolationTest` files.
- Use Pest's `beforeEach()` and `afterEach()` hooks for consistent setup/teardown rather than repeating boilerplate.

## 3. Frontend Testing (Vitest / React / Next.js)

- Use `@testing-library/react` with Vitest for component testing. Prefer `screen.getByRole()` over `getByText()` for accessibility-aligned queries.
- Mock Server Actions and API calls using `vi.mock()` or MSW (Mock Service Worker) for network-level interception.
- Test Server Components by verifying their rendered output using `renderToString` or dedicated RSC testing utilities.
- Test Client Components with full user interaction flows using `userEvent` (not `fireEvent`) for realistic event simulation.
- Use `vi.fn()` for callbacks and `vi.spyOn()` for module-level function interception.

## 4. E2E Testing (Playwright)

- Adopt the **Page Object Model (POM)** pattern: encapsulate page interactions in reusable classes (e.g., `LoginPage`, `DashboardPage`) to reduce duplication and improve maintainability.
- Use Playwright's `test.describe()` for grouping related scenarios and `test.beforeEach()` for authentication setup via storage state injection.
- Configure Playwright for multi-browser testing (Chromium, Firefox, WebKit) in CI. Run only Chromium locally for speed.
- Implement **visual regression testing** sparingly — only for critical UI surfaces (checkout, onboarding). Store baseline screenshots in the repository under `tests/e2e/screenshots/`.
- Use `playwright.config.ts` with `retries: 2` in CI to handle flaky tests without masking real failures.
- Set `timeout: 30_000` for E2E tests and `actionTimeout: 10_000` for individual interactions.

## 5. TDD Workflow & Coverage

- Practice Test-Driven Development (TDD) for complex business logic: write the failing test first, implement the minimum code to pass, then refactor.
- Enforce strict coverage thresholds in the CI pipeline:
  - **Core business logic:** minimum 80% line coverage.
  - **API endpoints:** minimum 90% coverage.
  - **Overall project:** minimum 70% coverage (gradually increase).
- Configure Vitest coverage via `@vitest/coverage-v8` with `coverage.include` and `coverage.exclude` patterns.
- Configure Pest coverage via `--coverage` flag with `--min-coverage=70` enforcement in CI.
- Track coverage trends over time; alert on regression exceeding 2% drop between commits.

## 6. Test Data & Snapshot Management

- Use dedicated test data factories (not ad-hoc data in test bodies) for consistency and maintainability.
- Use snapshot testing sparingly and only for stable, serializable outputs (API responses, email templates). Review snapshot diffs carefully before updating.
- NEVER commit snapshot updates without understanding why the output changed.
- Regenerate snapshots after intentional schema or UI changes — never force-update blindly.

## 7. Hard Constraints

- NEVER write tests that depend on a live external API; always mock them.
- NEVER skip tests (`->skip()` or `test.skip()`) in the `main` branch without a linked issue.
- ALWAYS use Pest syntax for Laravel tests instead of traditional PHPUnit class structures.
- NEVER use `@testing-library/react`'s `fireEvent`; use `@testing-library/user-event` for realistic user simulation.
- ALWAYS run the full test suite before merging to `main` — partial runs are for local development only.

---

## ✅ TESTING STANDARDS COMPLIANCE CHECK (Mandatory)
- [ ] **Syntax:** Are all backend tests written using Pest 3+ syntax?
- [ ] **Isolation:** Do tests run independently without shared state failures?
- [ ] **Mocking:** Are all third-party network calls mocked?
- [ ] **E2E Architecture:** Are Playwright tests using Page Object Models with proper multi-browser CI config?
- [ ] **Coverage:** Are minimum coverage thresholds enforced in CI with trend monitoring?
- [ ] **Test Pyramid:** Is the distribution weighted toward unit tests (70/20/10)?
- [ ] **Frontend Quality:** Are components tested with `userEvent` and accessibility-aligned queries?
