[TECH] neon
[OBJ] Neon — serverless Postgres platform with branching, autoscaling, point-in-time restore, and connection pooling via PgBouncer.
[RULES]
1. [REQ] Use Neon branches for development. Create a branch from `main` for each feature/migration: `neon branches create <name> --parent main`.
2. [REQ] Use the pooled connection string (`-pooler` endpoint) for application runtime. Use the direct connection string only for migrations and tools that require persistent sessions.
3. [REQ] Enable autoscaling on compute endpoints for variable workloads. Set min/max CU (compute units) to control cost and performance bounds.
4. [REQ] Use `neon branches restore <branch> --timestamp <ISO8601>` for point-in-time restore. Verify the timestamp is within the retention window.
5. [REQ] Use cascade deletes explicitly in schema (`ON DELETE CASCADE`) only when the child has no independent lifecycle. Prefer application-layer cascade for auditability.
6. [REQ] Use `@neondatabase/serverless` driver for serverless/edge deployments (Cloudflare Workers, Vercel Edge). Configure with `neonConfig` for WebSocket proxy.
7. [REQ] For ORMs (Prisma, Drizzle), use `@prisma/adapter-neon` or `neon-http` adapter. Set `directUrl` to the non-pooled string for migrations.
8. [REQ] Use `neon db import <file>` for bulk data loading. Use `COPY` for large CSV imports instead of individual `INSERT` statements.
9. [REQ] Use `neon schema diff <branch1> <branch2>` to review schema changes before merging a branch back to `main`.
10. [REQ] Configure connection pooler mode (`pgbouncer` or `pooler`) based on workload. `pgbouncer` for transaction-mode pooling; use `pooler` for session-mode when needed.
11. [REQ] Use `neon branches reset <branch> --parent main` to sync a stale development branch with the latest `main` schema and data.
12. [REQ] Set `idle_timeout` on compute endpoints to auto-suspend idle databases. This reduces cost for development branches.
13. [REQ] Use `neon auth` integration for JWT-based row-level security when building multi-tenant apps with per-user isolation.
14. [PROHIBIT] Never use the pooled connection string for schema migrations. PgBouncer transaction-mode does not support session-level operations like `CREATE DATABASE` or `LISTEN/NOTIFY`.
15. [PROHIBIT] Never run unbounded `SELECT` queries without `LIMIT`. Autoscaling can spike compute costs on large result sets.
[COMPAT]
- v2024.x: PostgreSQL 17, branching, autoscaling, point-in-time restore, PgBouncer pooling.
- Drivers: `@neondatabase/serverless` (JS/Edge), `pg` (Node), `neon` CLI.
- ORMs: Prisma 6+ (`@prisma/adapter-neon`), Drizzle ORM (`neon-http`, `neon-serverless`), Kysely.
- Limits: Max 10,000 connections per endpoint (pooled). Compute auto-suspend after idle timeout.
[REFS]
- https://neon.tech/docs
- https://neon.tech/docs/introduction/branching
- https://neon.tech/docs/introduction/autoscaling
- https://neon.tech/docs/connect/connection-pooling
- https://neon.tech/docs/import/import-data
- https://github.com/neondatabase/serverless
