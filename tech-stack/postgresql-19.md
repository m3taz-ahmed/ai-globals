[TECH] PostgreSQL 19 (Beta 3, Aug 2026 — GA expected Sep/Oct 2026) [!SPECULATIVE]
[OBJ] PostgreSQL 19.x — builds on PG 18 async I/O subsystem. `io_method=worker` auto-scales I/O workers, improved buffer eviction, more indexable queries, enhanced time-series support.
[RULES]
1. [REQ] Use `io_method=worker` with auto-scaling: `io_min_workers` + `io_max_workers` config — automatically scales I/O workers based on workload.
2. [REQ] Use `CREATE INDEX CONCURRENTLY` for production index creation (no table lock). Use `REINDEX CONCURRENTLY` for index rebuilds.
3. [REQ] Use `EXPLAIN (ANALYZE, BUFFERS)` for query tuning. Check `Seq Scan` on large tables.
4. [REQ] Use `uuidv7()` for time-ordered UUIDs — database-friendly, sortable, index-friendly.
5. [REQ] Use virtual generated columns: `GENERATED ALWAYS AS (expr) VIRTUAL` — computed on read, not stored.
6. [REQ] Use `pg_upgrade` with `--link` mode for fast in-place upgrade (requires same filesystem).
7. [REQ] Use logical replication for zero-downtime migrations: `pg_logical` slot + subscription.
8. [REQ] Use `pgvector` extension for vector similarity search: `CREATE EXTENSION vector;` — supports ivfflat + hnsw indexes.
9. [REQ] Use `pg_partman` for time-series partitioning — automatic partition creation + maintenance.
10. [REQ] Use connection pooling: `pgbouncer` (transaction mode) or `pgcat` for multi-tenant.
11. [PROHIBIT] Never run PG 19 Beta in production — wait for GA release (expected Sep/Oct 2026).
12. [PROHIBIT] Never use `SELECT *` in production queries — explicit column lists only.
[COMPAT]
- PostgreSQL 19 Beta 3 (released Aug 13 2026). GA expected Sep/Oct 2026.
- PG 18.6 is the latest stable (Aug 2026).
- PG 17.11, 16.15, 15.19, 14.24 also supported.
- Python 3.12-3.14 supported (for PL/Python).
[REFS]
- https://www.postgresql.org/docs/19/release-19.html
- https://www.postgresql.org/about/news/postgresql-186-1711-1615-1519-1424-and-19-beta-3-released-3365/
- https://www.postgresql.org/docs/
