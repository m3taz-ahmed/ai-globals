[TECH] clickhouse-analytics
[OBJ] ClickHouse Analytics.
[RULES]
1. [REQ] Engines: Use `MergeTree` family. `ReplacingMergeTree` for deduplication. Strict Partition keys (month/week).
2. [REQ] Ingestion: Batch inserts ONLY (min 10,000 rows/5s). Queue in Redis, flush via Laravel job.
3. [REQ] Querying: Use Materialized Views for heavy aggregations. Explicit TTL for retention.
4. [PROHIBIT] Hard Constraints: NEVER execute `UPDATE`/`DELETE` frequently. NEVER do unbounded `SELECT *` without partition filters.
