[TECH] database-scaling
[OBJ] Database Scaling & Operations (PostgreSQL).
[RULES]
1. [REQ] Connection `[PERF-09]`: Read/Write replica routing. PgBouncer/RDS Proxy (200-500 max). `sslnegotiation=direct` (PG17).
2. [REQ] Indexing `[PERF-10]`: JSONB (`jsonb_path_ops`). Partition >10M rows. `CREATE INDEX CONCURRENTLY` for zero downtime.
3. [REQ] Vacuum `[PERF-11]`: Aggressive autovacuum (0.01 vacuum, 0.005 analyze). Monitor PG17 `pg_wait_events`.
