# Performance & Scalability Standards

## 1. DATABASE PERFORMANCE
- **N+1 Prevention:** Never execute queries inside loops. Use Eager Loading (`with()`).
- **Indexing:** Every column in a `WHERE`, `JOIN`, or `ORDER BY` clause MUST be indexed.
- **Partitioning:** For tables exceeding 10M rows, implement database-level partitioning by date or ID range.
- **Query Budgets:** No single query should exceed 100ms in production. Use `EXPLAIN` to optimize slow queries.

## 2. CACHING STRATEGY
- **L1 Cache (In-Memory):** Use Laravel's `array` driver for request-lifecycle caching.
- **L2 Cache (Distributed):** Use Redis for cross-request caching.
- **Tags:** Use cache tags (`Cache::tags()`) for grouped invalidation.
- **TTL:** Set explicit Time-To-Live for all cache entries. Avoid indefinite caching.

## 3. ASYNC PROCESSING
- **Queue Everything:** Offload any task longer than 100ms to background queues (Emails, PDFs, API calls).
- **Concurrency:** Configure multiple queue workers to handle high throughput.
- **Throttling:** Use `RateLimited` jobs for external APIs to prevent 429 errors.

## 4. FRONTEND OPTIMIZATION
- **Asset Loading:** Use Vite for code-splitting and minification.
- **Critical CSS:** Inline critical CSS to improve First Contentful Paint (FCP).
- **Lazy Loading:** Use native `loading="lazy"` for images and `wire:navigate` for fast page transitions.
