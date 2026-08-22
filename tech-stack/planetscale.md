[TECH] planetscale
[OBJ] PlanetScale — MySQL-compatible serverless database platform built on Vitess with branching, deploy requests, and connection pooling.
[RULES]
1. [REQ] Use database branches for development. Create a branch from `main` for every feature/migration. Never apply schema changes directly to `main`.
2. [REQ] Submit schema changes via deploy requests. Review the diff, then promote the branch to `main` using `pscale deploy-request promote <db> <nr>`.
3. [REQ] Use connection pooling via the PlanetScale proxy URL for serverless/edge deployments. Never open more connections than your plan's limit.
4. [REQ] Use `pscale branch create <db> <branch>` and `pscale branch switch` for local development with `pscale connect <db> <branch> --port 3306`.
5. [REQ] Schema changes must be backward-compatible. PlanetScale uses online schema changes (gh-ost / Vitess VReplication) — no locking migrations.
6. [REQ] Add `ALTER TABLE` migrations as separate deploy requests. One schema change per deploy request for clean review and rollback.
7. [REQ] Use `pscale shell <db> <branch>` for ad-hoc queries in development. Never run exploratory queries against `main` in production.
8. [REQ] Enable `safe_migrations` on production databases. This blocks direct DDL on `main` and forces the deploy-request workflow.
9. [REQ] Use Vitess-compatible SQL. Avoid `FOREIGN KEY` constraints (not enforced by Vitess). Enforce referential integrity at the application layer.
10. [REQ] Use `pscale backup create <db> <branch>` for point-in-time backups before major migrations. Verify with `pscale backup show`.
11. [REQ] Use the `@planetscale/database` driver (JS/TS) or `mysql2` with connection pooling for serverless functions. Pass `url` from env, never hardcode credentials.
12. [REQ] For ORMs (Prisma, Drizzle), configure with `directUrl` for migrations and pooled connection string for runtime queries.
13. [REQ] Use `pscale org switch <org>` before any CLI operation when managing multiple organizations.
14. [PROHIBIT] Never use `DROP TABLE` or destructive `DELETE` without a backup and explicit approval. PlanetScale does not support `FLASHBACK`.
15. [PROHIBIT] Never use `SELECT *` in production queries. Always project explicit columns to avoid full table scans on sharded data.
[COMPAT]
- v2024.x: Vitess 19+, MySQL 8.0 compatibility, branching, deploy requests, connection pooling.
- Drivers: `@planetscale/database` (JS), `mysql2` (Node), `pscale` CLI.
- ORMs: Prisma 6+ (with `@prisma/adapter-planetscale`), Drizzle ORM, Kysely.
- Limits: No foreign key constraints. No `SAVEPOINT`. No `XA` transactions. No triggers.
[REFS]
- https://planetscale.com/docs
- https://planetscale.com/docs/concepts/branching
- https://planetscale.com/docs/concepts/deploy-requests
- https://planetscale.com/docs/concepts/connection-pooling
- https://vitess.io/docs/
- https://github.com/planetscale/database-js
