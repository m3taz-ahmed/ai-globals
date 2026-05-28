# Performance & Scalability Standards
> [!NOTE]
> Trigger: database schema design, optimization, or queue tasks.

## Database & Query Budget `[PERF-01]` `[PERF-10]`
- **N+1 Prevention:** Eager load with `with()`. ⛔ queries in loops. Enable `Model::shouldBeStrict()`.
- **Query Budget:** Max 100ms API transaction, 500ms job. Concurrent indexing `[PERF-10]`.
- **Partitioning `[PERF-11]`:** Partition tables over 10M rows.

## Caching Strategy `[PERF-06]`
- **Tiered Cache:** L1 (request memory) and L2 (Redis).
- **Stampede & Invalidation `[PERF-07]`:** Cache stampede prevention. Event-driven cache invalidation.
- **Failover `[PERF-08]`:** Circuit breaker graceful fallback to database.

## Async & Edge Optimization `[PERF-03]`
- **Queue First:** Offload heavy work (emails, PDFs, API calls) to Redis queues.
- **Vite & Memoization:** Code-splitting with Vite. Automatic React compiler memoization.
- **CDN Edge:** Push heavily-read APIs to CDN Edge with `Stale-While-Revalidate`.
