---
name: backend-design
description: Senior backend engineer reflexes — 13 disciplines covering think-before-coding, data modeling, migrations, queries, idempotency, errors, observability, security, auth, performance, debugging, testing, and boring-by-default
---
[SKILL] backend-design
[OBJ] Apply 13 senior backend engineering reflexes to every backend task — think before coding, model data with discipline, and ship boring, observable, secure systems.
[RULES]
1. [REQ] Reflex 1 — Think Before Coding: Run a 6-step pre-coding workflow before writing any implementation: (a) context+load — understand the request, data volume, and traffic profile; (b) data model — sketch entities, relationships, and invariants; (c) failure modes — list what breaks and how; (d) authorization — who can do what; (e) idempotence — can this be safely retried; (f) observability — what logs/metrics/alerts are needed.
2. [REQ] Reflex 2 — Data Modeling Discipline: Enforce invariants in the schema, not the application. Use CHECK constraints, FOREIGN KEYs, NOT NULL, and UNIQUE constraints. The database is the last line of defense.
3. [REQ] Reflex 3 — Migration Safety: Flag dangerous migrations (DROP COLUMN, ALTER TABLE on large tables, data backfills). Always provide a rollback plan. Expand-then-contract: deploy the new schema first, migrate code, then contract the old schema.
4. [REQ] Reflex 4 — Query Discipline: Detect and eliminate N+1 queries. Never run unbounded queries (SELECT * without LIMIT). Run EXPLAIN/EXPLAIN ANALYZE before shipping any new query. Add indexes for access patterns, not for every column.
5. [REQ] Reflex 5 — Idempotency and Side Effects: Design for idempotency from the start, not as cleanup. Use idempotency keys for payment/mutation endpoints. Side effects (emails, webhooks, writes) must be deduplicated or made safe to repeat.
6. [REQ] Reflex 6 — Error Handling as Design: Use structured errors with error codes, not try-catch soup. Define error categories (validation, not-found, conflict, auth, rate-limit, internal). Return consistent error shapes. Never swallow exceptions — log with context and re-raise or wrap.
7. [REQ] Reflex 7 — Observability by Default: Emit structured logs (JSON with context fields). Track RED metrics (Rate, Errors, Duration) for every endpoint. Provide health checks (liveness + readiness). Add distributed tracing for cross-service calls. Alert on symptoms, not causes.
8. [REQ] Reflex 8 — Security Discipline: Audit for IDOR (object-level authorization), mass assignment (whitelist fields), injection (parameterized queries, no string interpolation), and secret leaks (no secrets in logs, env vars, or error messages). Validate all inputs at the boundary.
9. [REQ] Reflex 9 — Auth and Authorization: Distinguish authentication (who are you) from authorization (what can you do). Enforce authz at the right layer — resource ownership at the data layer, role checks at the controller, feature flags at the service layer. Never trust client-side authorization.
10. [REQ] Reflex 10 — Performance and Scaling: Size for actual load, not hypothetical scale. Measure before optimizing. Identify the bottleneck (CPU, memory, I/O, network) before applying a fix. Cache only after identifying a measured cacheable pattern. Avoid premature optimization and premature abstraction.
11. [REQ] Reflex 11 — Debugging Discipline: Investigate with method, do not guess. Reproduce the issue reliably. Form a hypothesis, test it, observe the result. Use logs, metrics, and traces to narrow the scope. Change one variable at a time. Document the root cause and fix, not just the symptom.
12. [REQ] Reflex 12 — Testing with Discernment: Write tests that catch real regressions, not tests that decorate coverage metrics. Test behavior, not implementation. Cover happy path, edge cases, and failure modes. Integration tests for boundaries; unit tests for logic. Mock external dependencies at the seam, not internally.
13. [REQ] Reflex 13 — Boring by Default: Push back on premature complexity. Choose the boring, well-understood technology over the novel one unless there is a measured, specific reason. Prefer monoliths over microservices until scale demands otherwise. Prefer synchronous over async until throughput demands otherwise. Complexity must be earned, not assumed.
14. [REQ] Always — Route external library/framework questions through Context7 MCP before implementation.
15. [REQ] Always — Use parameterized queries; never interpolate user input into SQL.
16. [REQ] Always — Encrypt sensitive data at rest; use signed URLs for private assets.
17. [REQ] Always — Rate-limit public endpoints; throttle authentication attempts.
18. [REQ] Always — Use connection pooling; never open a new connection per request.
19. [REQ] Always — Set timeouts on all external calls (HTTP, DB, cache); never block indefinitely.
20. [REQ] Always — Use transactions for multi-step writes; never leave data in a partial state.
21. [REQ] Always — Version your API from day one; never make breaking changes without a migration path.
22. [PROHIBIT] Never ship a migration without a rollback plan.
23. [PROHIBIT] Never run unbounded queries (SELECT * without LIMIT).
24. [PROHIBIT] Never swallow exceptions or leave catch blocks empty.
25. [PROHIBIT] Never trust client-side authorization or client-provided IDs for ownership.
26. [PROHIBIT] Never optimize without measurement — guessing at bottlenecks wastes time.
27. [PROHIBIT] Never introduce complexity (microservices, event sourcing, CQRS) without a measured, specific justification.
28. [CMD] Context7 lookup: /postgres/postgres for schema constraints, EXPLAIN, indexing, and migration patterns.
29. [CMD] Context7 lookup: /redis/redis for caching patterns, pub/sub, rate limiting, and idempotency keys.
30. [REQ] Reflex 1 Detail — Context+Load: Document expected RPS, peak load, data volume, and growth trajectory before choosing architecture.
31. [REQ] Reflex 1 Detail — Data Model: Sketch the ER diagram; identify the hot path and the invariant each constraint protects.
32. [REQ] Reflex 1 Detail — Failure Modes: Enumerate cascading failure scenarios (DB down, cache miss storm, downstream timeout) and the mitigation for each.
33. [REQ] Reflex 2 Detail — Use database-level constraints for every invariant the business relies on; application validation is a complement, not a substitute.
34. [REQ] Reflex 2 Detail — Choose the right isolation level per transaction; default READ COMMITTED is not always sufficient.
35. [REQ] Reflex 3 Detail — Never run a data backfill in a single transaction on a large table; batch it with idempotent UPDATE statements.
36. [REQ] Reflex 3 Detail — Test the rollback plan on a staging copy before deploying the forward migration to production.
37. [REQ] Reflex 4 Detail — Use EXPLAIN ANALYZE on realistic data volumes, not an empty dev database; query plans change with table size.
38. [REQ] Reflex 5 Detail — Store idempotency keys with a TTL; expired keys should be garbage-collected, not kept forever.
39. [REQ] Reflex 6 Detail — Map every error code to an HTTP status and a user-facing message; never leak internal error details to the client.
40. [REQ] Reflex 7 Detail — Include request ID / trace ID in every log line for cross-correlation across services.
41. [REQ] Reflex 8 Detail — Audit for time-based attacks (timing-safe comparison for tokens) and SSRF on user-provided URLs.
42. [REQ] Reflex 9 Detail — Centralize authorization logic in policies/guards; never scatter permission checks ad hoc across handlers.
43. [REQ] Reflex 10 Detail — Load-test before and after optimization to prove the change had the intended effect.
44. [REQ] Reflex 11 Detail — Write a postmortem for every significant incident: timeline, root cause, action items, and owners.
45. [REQ] Reflex 12 Detail — Delete tests that provide no value; a suite full of trivial tests slows CI and erodes trust in the signal.
46. [REQ] Reflex 13 Detail — Document the "complexity budget" — every new framework, pattern, or service must justify its cognitive cost.
47. [PROHIBIT] Never deploy a forward migration without having tested its rollback on staging.
48. [PROHIBIT] Never add an index without confirming the query it optimizes and measuring the write overhead.
49. [PROHIBIT] Never log secrets, tokens, passwords, or PII — scrub them before they reach the log pipeline.
50. [PROHIBIT] Never use SELECT * in production queries — enumerate columns explicitly.
51. [PROHIBIT] Never skip the 6-step pre-coding workflow even for "small" changes — small changes cause outages too.
