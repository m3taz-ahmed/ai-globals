# Performance & Scalability Standards
> [!NOTE]
> **TRIGGER:** LOAD ON DATABASE SCHEMA DESIGN, OPTIMIZATION, OR QUEUE TASKS.
> **SCOPE:** N+1 PREVENTION, INDEXING, AND CACHING.

## 1. DATABASE PERFORMANCE
- **N+1 Prevention:** Never execute queries inside loops. Use Eager Loading (`with()`) and strict mode `Model::shouldBeStrict()`.
- **Indexing:** Every column in a `WHERE`, `JOIN`, or `ORDER BY` clause MUST be indexed.
- **Partitioning:** For tables exceeding 10M rows, implement database-level partitioning by date or ID range.
- **Query Budgets:** No single query should exceed 50ms in production. Use `EXPLAIN ANALYZE` to optimize slow queries.

## 2. CACHING STRATEGY
- **L1 Cache (In-Memory):** Use Laravel's `array` driver for request-lifecycle caching.
- **L2 Cache (Distributed):** Use Redis for cross-request caching.
- **Tags:** Use cache tags (`Cache::tags()`) for grouped invalidation.
- **TTL:** Set explicit Time-To-Live for all cache entries. Avoid indefinite caching.
- **TTL:** Set explicit Time-To-Live for all cache entries. Avoid indefinite caching.

## 3. ASYNC PROCESSING
- **Queue Everything:** Offload any task longer than 100ms to background queues (Emails, PDFs, API calls).
- **Concurrency:** Configure multiple queue workers to handle high throughput.
- **Throttling:** Use `RateLimited` jobs for external APIs to prevent 429 errors.

## 4. FRONTEND & EDGE OPTIMIZATION
- **Asset Loading:** Use Vite and Turbopack for code-splitting and minification.
- **Critical CSS:** Inline critical CSS to improve First Contentful Paint (FCP).
- **Edge Caching:** Push heavily read APIs to CDN Edge nodes using `Stale-While-Revalidate`.
- **React Compiler:** Rely on React Compiler (Next.js 15+) for automatic memoization rather than manual `useMemo`.

## 5. LOGIC-LOGGING INTERLOCK
- **Contextual Sequence:** When performing destructive parsing (e.g., PHP 8.3 `json_decode` with local consumption), the RAW payload MUST be logged *before* transformation if the logic fails. 
- **Just-In-Time Serialization:** Avoid serializing entire "God Objects" into logs. Log only the surgical context required to reproduce the failure.
---

## ⚡ PERFORMANCE CHECKLIST (Mandatory)
- [ ] **Queries:** Did I check for N+1 issues and use `with()` where needed?
- [ ] **Indexing:** Are all columns in the `WHERE` clause indexed?
- [ ] **Async:** Are long-running tasks (Emails/PDFs) pushed to the queue?
- [ ] **Cache:** Is any redundant computation or external fetch cached with a TTL?
