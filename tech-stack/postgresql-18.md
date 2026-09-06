[TECH] PostgreSQL 18
[OBJ] PostgreSQL 18.x (released Sep 2025, latest 18.6 Aug 2026). 3x I/O performance, virtual generated columns, uuidv7, accelerated upgrades, more indexable queries. PG 19 in beta 3.
[RULES]
1. [REQ] Leverage 3x I/O performance improvements: async I/O (`io_method=worker`), improved buffer eviction, streaming I/O for seq scans + VACUUM. Benchmark workloads — many OLTP/read-heavy apps see 2-3x throughput.
2. [REQ] Use virtual generated columns: `GENERATED ALWAYS AS (expr) VIRTUAL` — computed on read, not stored. Saves disk vs stored generated columns. Use for derived data accessed occasionally.
3. [REQ] Use `uuidv7` for time-ordered UUIDs: `gen_random_uuid_v7()` — database-friendly, sortable, index-friendly (vs random `uuidv4` which fragments indexes). Prefer for PKs in high-write tables.
4. [REQ] Use accelerated upgrade times: `pg_upgrade` optimized for large databases. Test upgrade on replica first; use `--link` mode for fast in-place upgrade (requires same filesystem).
5. [REQ] More queries can use indexes: planner improvements enable index usage for `OR` conditions, `IS NOT NULL` checks, and complex expressions. Re-run `EXPLAIN ANALYZE` on slow queries post-upgrade.
6. [REQ] Use `CREATE INDEX CONCURRENTLY` for production index creation (no table lock). Use `REINDEX CONCURRENTLY` for index rebuilds.
7. [REQ] Use `EXPLAIN (ANALYZE, BUFFERS)` for query tuning. Check `Seq Scan` on large tables, high `shared hit blocks` vs `read blocks`.
8. [REQ] Use connection pooling: `PgBouncer` (transaction-mode) or `pgcat` for multi-tenant. Set `max_connections` conservatively; rely on pooler.
9. [REQ] Use `pgvector` extension for vector/embedding storage: `vector(1536)` type, `<->` (L2), `<#>` (inner product), `<=>` (cosine) operators. HNSW index for ANN.
10. [REQ] Use `LISTEN` / `NOTIFY` for lightweight pub/sub. For high-throughput, use PostgresMQ / pgmq extension.
11. [REQ] Use `pg_partman` for time-series partitioning: `create_parent()` with weekly/monthly partitions. Auto-rotate old partitions.
12. [REQ] Use logical replication (`pglogical` / native) for zero-downtime migrations + read replicas. `wal_level=logical` required.
13. [REQ] Use `pg_stat_statements` for query performance monitoring. `pg_stat_activity` for active queries. `pg_locks` for lock analysis.
14. [REQ] Configure `shared_buffers = 25% RAM`, `effective_cache_size = 75% RAM`, `work_mem = 4-16MB`, `maintenance_work_mem = 256MB-1GB`. Tune `max_parallel_workers` for CPU count.
15. [REQ] Use `VACUUM` + `ANALYZE` regularly. Enable `autovacuum` (default). Monitor bloat with `pgstattuple`.
16. [CMD] `pg_upgrade -b /old/bin -B /new/bin -d /old/data -D /new/data --link` in-place upgrade.
17. [CMD] `CREATE EXTENSION IF NOT EXISTS pgvector;` install pgvector.
18. [CMD] `SELECT gen_random_uuid_v7();` generate time-ordered UUID.
19. [PROHIBIT] Never use `uuidv4` for high-write PKs — causes index fragmentation. Use `uuidv7` or `bigserial`.
20. [PROHIBIT] Never run `VACUUM FULL` in production (exclusive lock) — use `pg_repack` for online bloat removal.
21. [PROHIBIT] Never use `SELECT *` in production queries — explicit column lists for performance + stability.
22. [PROHIBIT] Never store passwords in plaintext — use `pgcrypto` `crypt()` with `gen_salt('bf')`.
[COMPAT]
- PostgreSQL 18.x (released Sep 2025, latest 18.6 Aug 2026).
- PostgreSQL 19 in beta 3 (release late 2026).
- Extensions: pgvector 0.8+, postgis 3.5+, pg_partman 5.2+, pg_stat_statements 1.11+.
- Drivers: psycopg 3.2+, asyncpg 0.30+, node-postgres 8.12+.
[REFS]
- https://www.postgresql.org/docs/18/
- https://www.postgresql.org/about/news/postgresql-18-released/
- https://www.postgresql.org/docs/18/ddl-generated-columns.html
- https://github.com/pgvector/pgvector
