# Testing Standards & Quality Assurance
> [!NOTE]
> Trigger: writing tests, CI/CD pipeline setup, QA workflows, test debugging.

## Backend & Frontend Frameworks `[TEST-04]`
- **Backend:** Pest 3+ for Laravel backend. expressive functional syntax, isolated database (`RefreshDatabase`).
- **Frontend:** Vitest + `@testing-library/react`. Use `userEvent` (not `fireEvent`), accessibility queries (`screen.getByRole`).

## End-to-End (E2E) Testing `[TEST-05]`
- **Playwright:** Adhere to Page Object Model (POM) pattern for critical journeys (checkout, signup).
- **Mocks:** Mock external services (`Http::fake()`, MSW). ⛔ live API requests in tests.

## Coverage & Constraints `[TEST-06]`
- **Gates:** CI enforcement: core business logic (80%+), APIs (90%+), overall (70%+).
- **Isolation:** Tests must not depend on order.
- **Strict rule:** ⛔ skip tests without a linked issue.
