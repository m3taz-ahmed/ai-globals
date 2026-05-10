# Tech-Stack: ClickHouse Analytics

> [!NOTE]
> **TRIGGER:** LOAD ON analytical data modeling, time-series events, high-volume ingestion.
> **SCOPE:** ClickHouse, analytical queries, integration with Laravel 12/13.

## 1. Table Engines & Modeling
- Use the `MergeTree` family of table engines for almost all analytical workloads.
- Use `ReplacingMergeTree` or `CollapsingMergeTree` for mutable event streams or deduplication.
- Design strict Partitioning keys (usually by month or week) to optimize data dropping and query speed.
- Avoid using JOINs for large datasets; denormalize data into wide tables at ingestion time.

## 2. Data Ingestion
- Batch inserts are mandatory. Never send single-row inserts to ClickHouse.
- Use Laravel 12/13 queued jobs to accumulate events in Redis, then flush them in bulk to ClickHouse via a scheduled command.
- Utilize the Laravel Context API to ensure all inserted events have proper trace IDs and tenant context.

## 3. Querying & Operations
- Use Materialized Views to compute aggregations incrementally at insertion time, vastly speeding up dashboard queries.
- Define explicit TTL (Time-To-Live) retention policies on tables to automatically drop old partitions and save disk space.
- Integrate with Datadog or Grafana for visualizing the time-series data.

## 4. Hard Constraints
- NEVER execute `UPDATE` or `DELETE` mutations frequently; ClickHouse mutations are heavy operations.
- NEVER execute unbounded `SELECT *` queries; always filter by partition keys (e.g., a date range).
- ALWAYS batch inserts (e.g., minimum 10,000 rows or every 5 seconds).

---

## ✅ CLICKHOUSE ANALYTICS COMPLIANCE CHECK (Mandatory)
- [ ] **Ingestion:** Are inserts batched appropriately instead of single-row inserts?
- [ ] **Modeling:** Are tables properly partitioned and denormalized?
- [ ] **Performance:** Are Materialized Views used for heavy aggregations?
