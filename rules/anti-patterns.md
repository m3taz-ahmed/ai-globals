# Anti-Patterns & Negative Constraints (Strictly Forbidden)
> [!NOTE]
> Trigger: Load on every code gen / edit. Applies to all projects. Every rule is a hard stop.
> See `rules/vocabulary.md` for core `[XXX-YY]` constraints. The below are structural additions.

## 1. Code Structure & Database
- ⛔ Business logic in Controllers. Controllers call Services/Actions only.
- ⛔ Duplicating code 3+ locations. Extract to shared utility.
- ⛔ Commented-out code or `TODO`/`FIXME` without ticket (e.g. `TODO(FS-42)`).
- ⛔ Tables without a primary key. Foreign keys without `constrained()`.
- ⛔ Migrations without a working `down()` method.
- ⛔ `nullable()` columns without explicit business reason. Default to `NOT NULL`.
- ⛔ Floats/doubles for currency. Use `decimal(10, 2)` or integer cents.
- ⛔ `TEXT`/`LONGTEXT` for indexed/searched columns. Use `VARCHAR` + length.

## 2. Error Handling & Security
- ⛔ suppresses (`@`) in PHP. Handle properly.
- ⛔ Empty `catch {}`. Log, re-throw, or handle explicitly.
- ⛔ Silently swallowing queue exceptions. Must log and monitor.
- ⛔ Returning `null` without documenting why in type/PHPDoc.
- ⛔ Wildcard `*` in CORS origin. Whitelist specific domains.
- ⛔ Exposing internal errors (traces, SQL) in production API responses.
- ⛔ Plain text/reversible password storage. Use Argon2/bcrypt (`Hash::make()`).
- ⛔ Disabling CSRF on POST/PUT/DELETE without documented reasons.

## 3. Performance & Testing
- ⛔ `sleep()` or polling loops in web requests. Use events/WebSockets.
- ⛔ Setting PHP memory limit to `-1`. Limit explicitly.
- ⛔ Loading large files fully to memory. Stream them.
- ⛔ Tests depending on execution order or shared mutable state.
- ⛔ Mocking unowned classes. Wrap in interface, mock interface.

## 4. AI Workflow
- ⛔ Skipping tests/static analysis before completion.
- ⛔ Dependencies without documentation. Fail CI on HIGH/CRITICAL audits.
- ⛔ Mixing refactoring and feature work in same commit.
- ⛔ Printing unchanged code (use placeholders).
- ⛔ Multi-file execution without `subagent-driven-development` or `tdd-workflows` skills.

## 5. AI Generation Anti-Patterns (Guard Skills)
- ⛔ **Error Swallowing:** Never swallow errors with broad catch-all handling. Do not return `null`/`false` to hide failures.
- ⛔ **Hallucinated APIs:** Never guess or assume an API exists based on patterns. Verify every import, library method, and CLI flag against actual source before calling it.
- ⛔ **Hardcoded Success Returns:** Never return `{"status": "ok"}` or canned mock data in production code. If unimplemented, throw explicit `NotImplementedException` or fail gracefully.
- ⛔ **Copy-Paste Bugs:** Do not copy-from-similar without re-deriving logic. Null-semantic and off-by-one errors stem from blind copying.
- ⛔ **Premature Abstraction:** Do not add speculative optional parameters, feature flags, or generic interfaces without a present-day caller.
- ⛔ **Docs Hallucination:** Never document a function, flag, or behavior without verifying it exists in the code exactly as described. Unverifiable claims are forbidden.
