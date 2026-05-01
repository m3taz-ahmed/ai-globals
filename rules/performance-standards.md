# Performance Standards & Optimization Rules

## 1. DATABASE QUERY BUDGETS
- **Per Request:** Maximum 20 database queries per HTTP request. Use Laravel Debugbar or Telescope to monitor.
- **N+1 Zero Tolerance:** Eager load ALL relationships accessed in loops. Use `Model::shouldBeStrict()` in development.
- **Slow Queries:** Any query exceeding 500ms must be optimized (add indexes, rewrite, or cache results).
- **Pagination:** Never load unbounded result sets. All list endpoints MUST use pagination (default: 25, max: 100).

## 2. CACHING STRATEGY
- **Cache Layers:**
  - **Application Cache (Redis):** For frequently accessed, rarely changing data (settings, permissions, role lists). TTL: 1-24 hours.
  - **Query Cache:** For expensive aggregate queries (reports, dashboards). TTL: 5-30 minutes.
  - **Response Cache:** For public, static API responses. Use HTTP cache headers (`Cache-Control`, `ETag`).
  - **File/Array Cache:** Only for local development or single-server setups. Never in production with multiple servers.
- **Invalidation:** Cache invalidation must be explicit. Use tagged caching (`Cache::tags()`) or event-driven invalidation.

## 3. QUEUE & BACKGROUND JOBS
- **Offload Heavy Work:** Email sending, PDF generation, external API calls, report generation — ALL must be queued.
- **Retry Policy:** Set `$tries = 3` and `$backoff = [10, 60, 300]` (exponential backoff) for jobs that can fail.
- **Timeout:** Set `$timeout` per job based on expected execution time. Default: 60 seconds. Maximum: 900 seconds.
- **Unique Jobs:** Use `ShouldBeUnique` for jobs that should not run concurrently (e.g., report generation for the same entity).
- **Monitoring:** Track failed jobs. Alert on `failed_jobs` table exceeding threshold. Review and retry or delete weekly.

## 4. MEMORY & RESOURCE MANAGEMENT
- **PHP Memory:** Default memory limit: 128MB for web, 256MB for CLI/queue workers. Never set to `-1` (unlimited).
- **Large Data:** Use `chunk()`, `lazy()`, or `cursor()` for processing datasets >1000 rows. Never `Model::all()` on large tables.
- **File Uploads:** Stream large file uploads to storage. Do not load entire file into memory.
- **Connection Pooling:** Use persistent database connections in queue workers. Close connections explicitly in long-running processes.

## 5. FRONTEND PERFORMANCE
- **Asset Budget:** Total JS bundle <250KB gzipped. Total CSS <50KB gzipped.
- **Lazy Loading:** Images below the fold MUST use `loading="lazy"`. Heavy JS components should be dynamically imported.
- **Critical CSS:** Inline critical above-the-fold CSS for initial render. Load remaining CSS asynchronously.
- **Web Vitals:** Target LCP <2.5s, FID <100ms, CLS <0.1 for all pages.
