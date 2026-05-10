# Tech-Stack: Database Scaling

> [!NOTE]
> **TRIGGER:** LOAD ON database architecture, query optimization, high-load scaling, PostgreSQL tuning.
> **SCOPE:** PostgreSQL 17, Aurora Serverless v2, Laravel 12/13, Advanced Indexing & Vacuuming.

## 1. Connection & Routing

- Enforce **Read Replica Routing**: configure Laravel 12/13 to separate Read and Write database connections via the `read`/`write` config split.
- Mandate **Connection Pooling** (PgBouncer in `transaction` mode or RDS Proxy) to prevent exhausting database connections under high concurrent load. Target max 200–500 connections per pool depending on instance size.
- Leverage Aurora Serverless v2 ACU scaling policies for dynamic workload management. Set min ACUs to avoid cold-start latency on idle databases.
- For Aurora: consider **Aurora I/O-Optimized** configuration for I/O-intensive workloads to achieve predictable pricing and eliminate per-I/O charges.
- Enable **`sslnegotiation=direct`** (PostgreSQL 17) for faster TLS handshakes, reducing connection establishment latency by up to 30%.

## 2. Query Performance & Indexing

- Enforce a strict **Query Budget**: maximum 100ms per transaction for critical API routes, maximum 500ms for background jobs.
- Schedule regular **Index Audits** using `pg_stat_statements` and `pg_stat_user_indexes` to identify missing, unused, or duplicate indexes.
- Implement **Table Partitioning** strategies (by range or hash) proactively for tables anticipated to exceed 10 million rows.
- **JSONB Indexing Strategy:**
  - Use **GIN indexes** (`jsonb_path_ops`) for containment queries (`@>`) on JSONB columns.
  - Use **B-tree indexes** on extracted JSONB paths (`(data->>'status')`) for equality/range queries.
  - Leverage PostgreSQL 17's `JSON_TABLE` function to convert JSONB into relational format for complex analytical queries.
- Leverage PG17's improved **B-tree multi-value lookup** for `IN`/`ANY` clauses — prefer `= ANY(ARRAY[...])` over long `IN` lists for better plan optimization.
- Use **Advisory Locks** (`pg_advisory_xact_lock`) for application-level distributed locking instead of `SELECT ... FOR UPDATE` on hot rows, reducing row-level contention.

## 3. Vacuum & Maintenance (PG17-Optimized)

- Tune **autovacuum** aggressively for high-churn tables:
  - `autovacuum_vacuum_scale_factor = 0.01` (default 0.2 is too lazy for large tables).
  - `autovacuum_analyze_scale_factor = 0.005`.
  - `autovacuum_vacuum_cost_delay = 2ms` (allow vacuum to work faster).
- Monitor vacuum progress via `pg_stat_progress_vacuum` and dead tuple counts via `pg_stat_user_tables`.
- Leverage PG17's **redesigned vacuum memory** (up to 20x less memory usage) — avoid over-allocating `maintenance_work_mem` which was necessary in older versions.
- Use `pg_wait_events` (PG17) to identify session bottlenecks and wait-time hotspots in real-time.

## 4. Backup & Recovery

- Leverage PG17's **incremental backup** support via `pg_basebackup --incremental` to capture only changes since the last backup, reducing storage costs and accelerating recovery for large databases.
- For Aurora: enable **backtrack** (point-in-time restore without snapshot recovery) for sub-minute RTO on accidental data corruption.
- Require automated, scheduled testing of Backup and Restore procedures to validate RTO objectives quarterly.
- Use **Aurora Global Database** for multi-region disaster recovery with <1s replication lag and automated failover.

## 5. Safety & Resilience

- Mandate **Migration Safety** protocols: use online DDL operations (`CONCURRENTLY`) for index creation to ensure zero-downtime.
- Monitor query plans continuously for regression as data volume grows. Alert on plan changes that increase estimated cost by >50%.
- Use PG17's improved **logical replication failover control** to maintain replication continuity after primary node failover without manual intervention.

## 6. Hard Constraints

- NEVER run schema changes (migrations) that lock heavily utilized tables during peak traffic hours.
- NEVER query the Write instance for heavy analytical reports; always route to Read replicas or ClickHouse.
- NEVER use `autovacuum_enabled = false` on production tables; tune parameters instead.
- ALWAYS use `CREATE INDEX CONCURRENTLY` for adding indexes to production tables.
- ALWAYS include `EXPLAIN ANALYZE` verification for any new query touching tables with >1M rows before deployment.

---

## ✅ DATABASE SCALING COMPLIANCE CHECK (Mandatory)
- [ ] **Routing:** Are read queries effectively offloaded to read replicas?
- [ ] **Pooling:** Is connection pooling (PgBouncer/RDS Proxy) active and configured in transaction mode?
- [ ] **Indexing:** Are JSONB columns indexed with GIN (`jsonb_path_ops`) or B-tree on extracted paths?
- [ ] **Vacuum:** Are autovacuum parameters tuned for high-churn tables (scale_factor ≤ 0.05)?
- [ ] **Backup:** Are incremental backups configured and restore procedures tested quarterly?
- [ ] **Safety:** Are all database migrations verified to be non-blocking (zero-downtime)?
- [ ] **Monitoring:** Are `pg_stat_statements` and `pg_wait_events` enabled for query and wait-time analysis?
