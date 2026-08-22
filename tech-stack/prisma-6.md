[TECH] Prisma 6
[OBJ] Type-safe ORM for Node.js/TypeScript with schema-first modeling, migrations, and query builder.
[RULES]
1. [REQ] Define all models in `schema.prisma` using the `model` block with explicit `@id`, `@map`, and `@@map` for table/column naming.
2. [REQ] Use `prisma migrate dev` for development schema changes and `prisma migrate deploy` for production deployments; never run `db push` in production.
3. [REQ] Use `prisma migrate reset` only in development; it drops all data and reapplies migrations.
4. [REQ] Wrap multi-operation writes in interactive transactions (`$transaction(async (tx) => { ... })`) with explicit timeout and retry on `P2034`.
5. [REQ] Use `select` to project only needed fields; avoid `include` + `select` on the same relation to prevent type ambiguity.
6. [REQ] Define relations with `@relation` and foreign key fields explicitly; use `onDelete: Cascade` only when the child has no independent lifecycle.
7. [REQ] Use `prisma db pull` to introspect existing databases, then review generated schema before committing.
8. [REQ] Configure `previewFeatures` in the generator block before using experimental features; remove them once promoted to GA.
9. [REQ] Use Prisma Accelerate (`@prisma/accelerate`) for connection pooling and edge caching in serverless/edge deployments; set `directUrl` for migrations.
10. [REQ] Use Prisma Pulse (`@prisma/pulse`) for real-time change streams via `prisma.$subscribe` or the Pulse client; authenticate with a Pulse API key.
11. [REQ] For edge runtimes (Cloudflare Workers, Vercel Edge), use `@prisma/client/edge` with Accelerate driver adapter; avoid native engine binaries.
12. [REQ] Use `prisma validate` in CI to verify schema integrity before merge.
13. [REQ] Handle `PrismaClientKnownRequestError` with specific `code` (e.g., `P2002` for unique violations) and log `meta` for debugging.
14. [PROHIBIT] Never instantiate multiple `PrismaClient` instances in the same process; use a singleton pattern to prevent connection pool exhaustion.
15. [PROHIBIT] Never use raw `$queryRaw` or `$executeRaw` with string interpolation; always use tagged templates or parameterized inputs to prevent SQL injection.
[COMPAT]
- v6.x: Node 18+, TypeScript 5.1+, PostgreSQL/MySQL/SQLite/MongoDB/SQL Server
- v6.x: Prisma Accelerate, Prisma Pulse, driver adapters (pg, @prisma/adapter-neon)
- v6.x: Edge runtime support (Cloudflare Workers, Vercel Edge, Deno Deploy)
[REFS]
- https://www.prisma.io/docs
- https://www.prisma.io/docs/concepts/components/prisma-schema
- https://www.prisma.io/docs/concepts/components/prisma-client
- https://www.prisma.io/docs/concepts/components/prisma-migrate
- https://www.prisma.io/docs/data-platform/accelerate
- https://www.prisma.io/docs/data-platform/pulse
