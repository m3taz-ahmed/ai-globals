[FILE] EXAMPLES
[OBJ] Real-world code patterns resolving anti-patterns.
[RULES]

[PATTERN] 1. Think Before Coding
- [PROHIBIT] Hidden Assumptions: Never export all records without filtering. Never leak PII (emails/phones).
- [REQ] Ask Scope: Verify format (CSV/JSON), filters, and PII exclusion before writing code.
- [REQ] Options: Present architectural choices (e.g., DB index vs Redis) instead of silently choosing.

[PATTERN] 2. Simplicity First
- [PROHIBIT] Over-Abstraction: No Strategy patterns for simple calculations.
- [PROHIBIT] Speculative Features: Do not add AuditLoggers or Events unless requested. Solve today's problem.

[PATTERN] 3. Surgical Changes
- [PROHIBIT] Drive-by Refactoring: Do not convert ES5 to ES6 or add types if unrequested.
- [REQ] Precision: Modify ONLY the buggy line. Match existing single/double quotes and styling.

[PATTERN] 4. Goal-Driven Execution
- [REQ] Verifiable Tests: Before fixing a bug, write a failing test (e.g. overlapping slots fail). Fix the code until test passes.

[PATTERN] 5. Laravel Security
- [PROHIBIT] Mass Assignment: No `guarded = []`. Use `fillable`.
- [PROHIBIT] N+1 Queries: Always use `with()` for eager loading.

[PATTERN] 6. React Security
- [PROHIBIT] XSS: Never use `dangerouslySetInnerHTML` without `DOMPurify`.
- [PROHIBIT] Client Data Leaks: Select explicit fields only. Never pass full user models with hashes to client.

[PATTERN] 7. SQL Injection
- [PROHIBIT] Raw Strings: Never interpolate strings in DB queries.
- [REQ] Bindings: Use Query Builder or explicit bindings `?`.
- [REQ] FormRequest: Use `$request->validated()` for writes, never `$request->all()`.

[PATTERN] 8. Prompt Master Templates
- [REQ] Standard Output: Use Capacity, Role, Insight, Statement, Personality, Experiment format.
- [REQ] CoT (Chain of Thought): Use `<thinking>` tags for logic tasks, BUT NEVER for o1/o3/Claude extended reasoning models.
