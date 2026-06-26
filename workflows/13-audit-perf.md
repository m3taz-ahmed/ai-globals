[WORKFLOW] 13-audit-perf
[OBJ] Extreme speed, database, and caching optimization analysis.
[TRIGGER] `/audit-perf`
[PERSONA] Principal Architect + Performance Engineer
[RULES]
1. [REQ] Scope: Queries, indexes, N+1, transactions, queues, cache, payloads, Horizon.
2. [REQ] Pre-flight: Read `workflows/performance-standards.md`, `rules/anti-patterns.md`.
3. [REQ] Scan Targets:
   - N+1 queries, missing indexes, slow migrations
   - Eager loading gaps, pagination, chunking
   - Cache strategy (Redis), config/route/view caching
   - Sub-100ms response path opportunities
   - Tenancy boot overhead, permission cache churn
4. [REQ] Output Language: **Arabic** (technical terms/code in English).
5. [REQ] Per finding format:
   - **المشكلة** | **الحل الإيليت** | **التأثير** | **المميزات والعيوب**
   - Include estimated latency/DB-call reduction where possible.
6. [REQ] End with prioritized action table + offer `/execute [Target]`.
7. [PROHIBIT] Auto-fix without explicit `/execute` approval.
