# Database Scaling & Operations
> [!NOTE]
> Trigger: database architecture, query optimization, high-load scaling, PostgreSQL tuning.

## Connection & Routing `[PERF-09]`
- **Replica Routing:** Separate Read/Write connections.
- **Connection Pooling:** PgBouncer (transaction mode) or RDS Proxy; target 200-500 max.
- **SSL direct:** Use `sslnegotiation=direct` (PostgreSQL 17) to reduce handshake latency.

## Query Performance & Indexing `[PERF-10]`
- **Query Budget:** API requests < 100ms, jobs < 500ms.
- **JSONB Indexes:** GIN index (`jsonb_path_ops`) or B-tree on extracted paths.
- **Table Partitioning:** Proactively partition tables exceeding 10M rows.
- **Safety:** Use `CREATE INDEX CONCURRENTLY` for zero-downtime.

## Vacuum & Maintenance `[PERF-11]`
- **Autovacuum Tuning:** aggressive thresholds (`scale_factor` 0.01 vacuum, 0.005 analyze, `delay` 2ms).
- **PG17 Memory:** Reduced vacuum memory footprint, monitor wait states via `pg_wait_events`.
- **Backup:** Use PG17 incremental backups (`pg_basebackup --incremental`).
