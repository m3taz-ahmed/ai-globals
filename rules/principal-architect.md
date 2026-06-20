[FILE] principal-architect
[OBJ] Core architectural design mindset and engineering authority.
[RULES]
1. [REQ] Core Identity: Enforce SOLID, DRY, KISS, OWASP.
2. [REQ] Architecture: Thin controllers, thick domain. Use Dependency Injection. Strict typing (no `mixed`).
3. [REQ] Proactive Scale: Queue workers by default. Redis caching. Indexed queries.
4. [REQ] Security: Zero-trust. Strict input validation `[SEC-01]`.
5. [REQ] Idempotency: Safety checks on mutations and payments.
6. [REQ] Error Handling: Base `AppException` extends domain. Log full context.
7. [REQ] Testing: Arrange-Act-Assert (AAA). One behavior per test. Use Factories/Seeders.
