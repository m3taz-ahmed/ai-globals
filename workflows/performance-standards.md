[WORKFLOW] performance-standards
[OBJ] Performance & Scalability Standards.
[RULES]
1. [REQ] DB Budget `[PERF-01]`: Eager load `with()`. Enable `Model::shouldBeStrict()`. Max 100ms API, 500ms job. Partition >10M rows.
2. [REQ] Caching `[PERF-06]`: Tiered (L1 Mem, L2 Redis). Prevent stampedes. Fallback to DB (Circuit Breaker).
3. [REQ] Async `[PERF-03]`: Offload heavy work to Redis queues. Vite code-splitting. Push APIs to CDN Edge.
