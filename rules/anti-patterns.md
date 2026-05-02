# Anti-Patterns & Negative Constraints (Strictly Forbidden)

> Every rule here is a **hard stop**. Violating any constraint below is equivalent to a failing test â€” the deliverable is rejected until corrected.

## 1. CODE STRUCTURE

- **NEVER** put business logic in Controllers. Controllers call Services/Actions â€” nothing more.
- **NEVER** use `$guarded = []` on any Eloquent Model. Always define `$fillable` explicitly.
- **NEVER** use `Model::all()` on tables expected to exceed 1,000 rows. Use pagination, `chunk()`, or `cursor()`.
- **NEVER** create "God Classes" exceeding 300 lines. Split into focused collaborators.
- **NEVER** create functions/methods exceeding 50 lines. Refactor into smaller, named units.
- **NEVER** use magic strings for statuses, types, or categories. Use PHP 8.1+ Enums or class constants.
- **NEVER** duplicate code across 3+ locations. Extract into a shared Service, Trait, or Helper.
- **NEVER** leave commented-out code in the codebase. Delete it â€” Git preserves history.
- **NEVER** use `TODO` or `FIXME` comments without a linked ticket number (e.g., `// TODO(FS-42): ...`).

## 2. ERROR HANDLING

- **NEVER** use `@` to suppress errors in PHP. Surface and handle them properly.
- **NEVER** use empty `catch {}` blocks. Every catch must log, re-throw, or handle explicitly.
- **NEVER** throw generic `\Exception` or `Error`. Use domain-specific exceptions extending `AppException`.
- **NEVER** swallow exceptions silently in queue jobs. Failed jobs must be logged and monitored.
- **NEVER** return `null` from a method without documenting why in the return type and PHPDoc.

## 3. SECURITY

- **NEVER** log sensitive data: passwords, tokens, API keys, credit card numbers, or PII in plain text.
- **NEVER** use `*` for CORS `Access-Control-Allow-Origin`. Whitelist specific domains.
- **NEVER** commit `.env` files, credentials, or secrets to version control.
- **NEVER** use raw string concatenation in SQL queries. Use Eloquent, Query Builder, or PDO parameterized queries.
- **NEVER** trust user input without validation. All inputs pass through FormRequest or explicit validation.
- **NEVER** expose internal error details (stack traces, SQL errors) in production API responses.
- **NEVER** store passwords in plain text or with reversible encryption. Use `Hash::make()` (bcrypt/argon2).
- **NEVER** disable CSRF protection on POST/PUT/DELETE routes without documented justification.

## 4. PERFORMANCE

- **NEVER** execute database queries inside loops (N+1 problem). Eager load with `with()`.
- **NEVER** skip pagination on list endpoints. Every list route must be paginated.
- **NEVER** run heavy operations synchronously in HTTP requests: email, PDF generation, external API calls, report generation â€” queue them.
- **NEVER** use `sleep()` or polling loops in web requests. Use events, queues, or WebSockets.
- **NEVER** set PHP memory limit to `-1` (unlimited). Configure explicit, reasonable limits.
- **NEVER** load entire file contents into memory for large uploads. Use streaming.

## 5. DATABASE

- **NEVER** create a table without a primary key.
- **NEVER** add a foreign key column without a corresponding `constrained()` foreign key constraint.
- **NEVER** write migrations without a working `down()` method for rollback.
- **NEVER** use `nullable()` on a column without a documented business reason. Default to `NOT NULL`.
- **NEVER** store monetary values as `float` or `double`. Use `decimal(10, 2)` or integer (cents).
- **NEVER** use `TEXT` or `LONGTEXT` columns for data that should be indexed or searched. Use `VARCHAR` with appropriate length.

## 6. TESTING

- **NEVER** deliver a new feature or bug fix without corresponding tests.
- **NEVER** hardcode IDs, timestamps, or dates in tests. Use Factories and `Carbon::setTestNow()`.
- **NEVER** write tests that depend on execution order or shared mutable state between test cases.
- **NEVER** mock what you don't own â€” wrap external dependencies behind interfaces, then mock the interface.

## 7. AI WORKFLOW (AGENT BEHAVIOR)

- **NEVER** rewrite entire files when only a few lines need changing. Use surgical diffs.
- **NEVER** generate code without stating assumptions and the plan first (if requirements are <80% clear).
- **NEVER** skip the verification step â€” run tests and static analysis before reporting completion.
- **NEVER** introduce a new dependency without documenting the justification.
- **NEVER** mix refactoring with feature work in the same commit/delivery.
- **NEVER** output unchanged code â€” use placeholders like `// ... existing code ...` to save context.
