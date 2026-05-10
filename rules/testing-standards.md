# Tech-Stack: Testing Standards

> [!NOTE]
> **TRIGGER:** LOAD ON writing tests, CI/CD pipeline setup, QA workflows.
> **SCOPE:** Pest 3+ (Laravel), Vitest (React), Playwright (E2E), TDD.

## 1. Test Pyramid & Frameworks
- Adhere to the Test Pyramid: many Unit tests, fewer Integration tests, and critical E2E tests.
- Use **Pest 3+** for all Laravel 12/13 backend testing (Feature + Unit). Use Pest's expressive, functional syntax.
- Use **Vitest** for Next.js/React component and utility testing.
- Use **Playwright** for critical end-to-end user journeys (e.g., checkout, signup).

## 2. Backend Testing (Pest / Laravel 12/13)
- Use Database Factories extensively to generate realistic test data.
- Ensure test isolation; tests must not depend on the order of execution or shared database state (use `RefreshDatabase`).
- Mock external services (Stripe, SES, third-party APIs) using Laravel's `Http::fake()` or mock objects to prevent network dependencies in CI.
- Test multi-tenant scenarios explicitly by asserting data isolation between tenant contexts.

## 3. TDD Workflow & Coverage
- Practice Test-Driven Development (TDD) for complex business logic.
- Enforce strict coverage thresholds (e.g., minimum 80% for core business logic) in the CI pipeline.

## 4. Hard Constraints
- NEVER write tests that depend on a live external API; always mock them.
- NEVER skip tests (`->skip()`) in the `main` branch without a linked Jira/Linear issue.
- ALWAYS use Pest syntax for Laravel tests instead of traditional PHPUnit class structures.

---

## ✅ TESTING STANDARDS COMPLIANCE CHECK (Mandatory)
- [ ] **Syntax:** Are all backend tests written using Pest 3+ syntax?
- [ ] **Isolation:** Do tests run independently without shared state failures?
- [ ] **Mocking:** Are all third-party network calls mocked?
