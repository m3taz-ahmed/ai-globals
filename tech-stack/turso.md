[TECH] turso
[OBJ] Turso — distributed edge database based on SQLite/libSQL with embedded replicas, multi-region replication, and schema migrations.
[RULES]
1. [REQ] Use `libSQL` client drivers (`@libsql/client` for JS/TS, `libsql` for Python, `libsql-client` for Go) — not raw `sqlite3`. LibSQL extends SQLite with replication and vector search.
2. [REQ] Use embedded replicas for read-heavy edge workloads. Call `client.sync()` periodically to pull updates from the primary. Embedded replicas are read-only locally.
3. [REQ] Route all writes to the primary database. Embedded replicas cannot accept writes — writes are forwarded to the primary automatically by the client.
4. [REQ] Use `turso db create <name> --location <region>` for primary creation. Use `turso db replicate <name> --location <region>` for read replicas in multiple regions.
5. [REQ] Use `turso db shell <name>` for ad-hoc queries. Use `turso db show <name> --url` and `--token` to retrieve connection strings for application config.
6. [REQ] Use Turso Platform API (`https://api.turso.tech`) for programmatic database management. Authenticate with the platform API token, never with the database token.
7. [REQ] Use `@libsql/client` with `authToken` from env for remote connections. For embedded replicas, use `createClient({ url, authToken, syncUrl })` with local file path.
8. [REQ] Use schema migrations via `drizzle-kit` or manual `CREATE TABLE` scripts. Turso does not have a built-in migration tool — manage migrations in your application code.
9. [REQ] Use `turso db tokens create <name>` to generate database-specific tokens. Use scoped tokens with `--expiration` for short-lived access in serverless environments.
10. [REQ] Use libSQL vector search (`vector32` type, `vector_distance_cos()`) for AI/RAG workloads. Create vector indexes with `CREATE INDEX ... USING libsql_vector_idx`.
11. [REQ] For multi-tenant SaaS, use Turso Groups (`turso group create <name>`) to manage database fleets with shared schema and per-tenant isolation.
12. [REQ] Use `turso db dump <name>` for logical backups. Store backups in object storage (S3/R2) for disaster recovery.
13. [REQ] Configure `sync_interval` on embedded replicas based on freshness requirements. Lower intervals increase read consistency but raise network overhead.
14. [PROHIBIT] Never use `PRAGMA wal_checkpoint` on embedded replicas — replication is managed by the libSQL client. Manual WAL operations break replication.
15. [PROHIBIT] Never store the database token in client-side code. Use a backend proxy or edge function to inject the token at runtime.
[COMPAT]
- v2024.x: libSQL (SQLite fork), embedded replicas, multi-region, vector search, Turso Platform API.
- Drivers: `@libsql/client` (JS/TS), `libsql` (Python), `libsql-client-go` (Go), `libsql-client` (Rust).
- ORMs: Drizzle ORM (`drizzle-orm/libsql`), Prisma 6+ (preview), Kysely.
- Limits: 500 databases per group (free tier: 3). Max DB size 9GB (free), 8TB (scaler). Embedded replicas require libSQL client.
[REFS]
- https://docs.turso.tech
- https://docs.turso.tech/libSQL
- https://docs.turso.tech/features/embedded-replicas
- https://docs.turso.tech/features/replication
- https://docs.turso.tech/platform
- https://docs.turso.tech/features/vector-search
- https://github.com/tursodatabase/libsql-client-ts
