# Anti-Patterns & Negative Constraints (Strictly Forbidden)
> [!NOTE]
> Trigger: Load on every code gen / edit. Applies to all projects. Every rule is a hard stop.
> Map of code definitions: see `rules/vocabulary.md`.

## 1. Code Structure
- ⛔ Business logic in Controllers. Controllers call Services/Actions only.
- ⛔ `$guarded = []` on models. Use `$fillable` explicitly. `[SEC-03]`
- ⛔ `Model::all()` on tables > 1000 rows. Use pagination/chunks. `[PERF-02]`
- ⛔ God Classes (>300 lines) or Methods (>30 lines). `[CODE-03]`
- ⛔ Magic strings for statuses/categories. Use Enums/constants. `[CODE-04]`
- ⛔ Duplicating code 3+ locations. Extract to shared utility.
- ⛔ Commented-out code or `TODO`/`FIXME` without ticket (e.g. `TODO(FS-42)`).

## 2. Error Handling
- ⛔ suppresses (`@`) in PHP. Handle properly.
- ⛔ Empty `catch {}`. Log, re-throw, or handle explicitly.
- ⛔ Throwing raw `\Exception` or `Error`. Use domain exceptions extending `AppException`. `[CODE-02]`
- ⛔ Silently swallowing queue exceptions. Must log and monitor.
- ⛔ Returning `null` without documenting why in type/PHPDoc. `[CODE-02]`

## 3. Security
- ⛔ Log sensitive data (passwords, tokens, PII) in plain text. `[SEC-04]`
- ⛔ Wildcard `*` in CORS origin. Whitelist specific domains.
- ⛔ Committing `.env` or credentials. `[SEC-04]`
- ⛔ Raw SQL concatenation. Use Eloquent, Query Builder, or PDO parameters. `[SEC-02]`
- ⛔ Untrusted input. All inputs must pass FormRequest or explicit validation. `[SEC-01]`
- ⛔ Exposing internal errors (traces, SQL) in production API responses.
- ⛔ Plain text/reversible password storage. Use Argon2/bcrypt (`Hash::make()`).
- ⛔ Disabling CSRF on POST/PUT/DELETE without documented reasons.

## 4. Performance
- ⛔ Database queries in loops (N+1). Eager load with `with()`. `[PERF-01]`
- ⛔ Unpaginated list endpoints. Paginate all list routes. `[PERF-02]`
- ⛔ Synchronous heavy work (emails, PDFs, external APIs). Queue them. `[PERF-03]`
- ⛔ `sleep()` or polling loops in web requests. Use events/WebSockets.
- ⛔ Setting PHP memory limit to `-1`. Limit explicitly.
- ⛔ Loading large files fully to memory. Stream them.

## 5. Database
- ⛔ Tables without a primary key.
- ⛔ Foreign keys without `constrained()` constraint.
- ⛔ Migrations without a working `down()` method.
- ⛔ `nullable()` columns without explicit business reason. Default to `NOT NULL`.
- ⛔ Floats/doubles for currency. Use `decimal(10, 2)` or integer cents.
- ⛔ `TEXT`/`LONGTEXT` for indexed/searched columns. Use `VARCHAR` + length.

## 6. Testing
- ⛔ Features/fixes without tests. `[TEST-01]`
- ⛔ Hardcoded dates/IDs. Use Factories and `Carbon::setTestNow()`. `[TEST-03]`
- ⛔ Tests depending on execution order or shared mutable state.
- ⛔ Mocking unowned classes. Wrap in interface, mock interface.

## 7. AI Workflow
- ⛔ Monolithic rewrites. Apply surgical diffs. `[BEH-03]`
- ⛔ Generating code without stating assumptions if clarity is <80%. `[BEH-01]`
- ⛔ Skipping tests/static analysis before completion.
- ⛔ Dependencies without documentation. Fail CI on HIGH/CRITICAL audits.
- ⛔ Mixing refactoring and feature work in same commit.
- ⛔ Printing unchanged code (use placeholders).
- ⛔ Multi-file execution without `subagent-driven-development` or `tdd-workflows` skills.
