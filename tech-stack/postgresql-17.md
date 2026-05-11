# Tech-Stack: PostgreSQL 17

> [!NOTE]
> **TRIGGER:** LOAD ON database migrations, query optimization, backend data modeling.
> **SCOPE:** PostgreSQL 17 for SaaS, Aurora Serverless v2 patterns. Scaling: ref `rules/database-scaling.md`.

## 1. Data Modeling & Types
- Leverage `JSONB` for schema-less attributes, but prefer relational columns for highly queried or indexed fields.
- Implement Table Partitioning (Range or Hash) for massive datasets (e.g., time-series data or multi-tenant activity logs).
- **Primary Keys:** Strictly use `UUIDv7` (natively supported in PG 18, use extensions in PG 17) or `ULID` as primary keys for timestamp-ordered, distributed scalability.

## 2. Querying & Indexing
- Use Partial Indexes for highly filtered queries (e.g., `CREATE INDEX ON users (email) WHERE active = true`).
- Implement **BRIN Indexes** for large, naturally ordered time-series datasets to drastically reduce index bloat.
- Implement GIN or GiST indexes for `JSONB` or full-text search requirements.
- Use Common Table Expressions (CTEs) to simplify complex hierarchical queries, but monitor for optimization fences.
- Utilize Window Functions for analytics (e.g., `ROW_NUMBER()`, `RANK()`, `SUM() OVER()`).

## 3. Operational & Security Patterns
- **Memory Tuning:** Set `shared_buffers` to approximately 25% of total RAM. Monitor with `pg_buffercache`.
- Enforce Row-Level Security (RLS) for tenant isolation when applicable.
- Leverage Connection Pooling via PgBouncer or RDS Proxy to manage Aurora connections.
- Analyze query performance using `pg_stat_statements` and `EXPLAIN ANALYZE`.

## 4. Hard Constraints
- NEVER run unbounded queries (always use pagination or limits).
- NEVER use `SELECT *` in production queries; always specify columns explicitly.
- ALWAYS verify query plans using `EXPLAIN ANALYZE` for complex joins or new indexes.

---

## ✅ POSTGRESQL 17 COMPLIANCE CHECK (Mandatory)
- [ ] **Indexing:** Are partial or specialized (GIN/GiST) indexes used where appropriate?
- [ ] **Performance:** Have complex queries been profiled with `EXPLAIN ANALYZE`?
- [ ] **Scalability:** Are large tables prepared for partitioning and using connection pooling?
