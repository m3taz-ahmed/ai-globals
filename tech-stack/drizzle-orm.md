[TECH] Drizzle ORM
[OBJ] Lightweight TypeScript SQL ORM with zero-overhead schema definition, type-safe queries, and dialect support for PostgreSQL, MySQL, and SQLite.
[RULES]
1. [REQ] Define schema using `pgTable`/`mysqlTable`/`sqliteTable` with explicit column types; use `.$type<>()` for custom TS types on columns.
2. [REQ] Use `drizzle-kit` for migrations: `drizzle-kit generate` to create SQL migration files, `drizzle-kit migrate` to apply them; commit migration files to VCS.
3. [REQ] Use `drizzle-kit push` for rapid prototyping only; prefer `generate` + `migrate` for production to maintain auditable migration history.
4. [REQ] Use `db.transaction(async (tx) => { ... })` for multi-statement atomicity; throw to rollback, return to commit.
5. [REQ] Define foreign keys with `references()` and explicit `onDelete`/`onUpdate` actions; avoid implicit cascade behavior.
6. [REQ] Use `select()` with explicit column lists for read queries; use `insert().values()`, `update().set()`, and `delete()` for writes with `.where()` filters.
7. [REQ] Use prepared statements (`db.execute(sql\`...\`)`) with `sql` template tag for raw queries; never concatenate user input into SQL strings.
8. [REQ] For Row Level Security (RLS), set `role` on the database connection and use `db.execute(sql\`SET LOCAL app.current_user = ${userId}\`)` to pass context; verify policies in PostgreSQL.
9. [REQ] Use `drizzle-studio` (`drizzle-kit studio`) for visual schema exploration and data inspection during development.
10. [REQ] Use relational queries API (`db.query.users.findMany({ with: { posts: true } })`) for nested reads; use `db.select()` for explicit joins when you need fine-grained control.
11. [REQ] Handle dialect-specific features: PostgreSQL arrays/JSONB/enum, MySQL JSON, SQLite blob; verify type mappings per dialect.
12. [REQ] Use connection pooling (PgBouncer, pgBouncer-mode on Neon, or `pool` config) for serverless deployments; configure `max` connections appropriately.
13. [REQ] Use `mode: 'default'` or `mode: 'planetscale'` for MySQL drivers; ensure driver matches your database provider.
14. [PROHIBIT] Never use `sql.raw()` with user input; it bypasses parameterization and enables SQL injection.
15. [PROHIBIT] Never run `drizzle-kit push` in production; it applies schema changes without generating migration files.
[COMPAT]
- v0.36+: PostgreSQL (node-postgres, postgres.js, Neon, Supabase, Vercel pg), MySQL (mysql2, PlanetScale), SQLite (better-sqlite3, libSQL/Turso, D1)
- v0.36+: Drizzle Kit (migrations, push, studio), Drizzle Zod (schema validation)
- v0.36+: Edge runtime support via `drizzle-orm/neon-serverless`, `drizzle-orm/d1`
[REFS]
- https://orm.drizzle.team/docs
- https://orm.drizzle.team/docs/sql-schema-declaration
- https://orm.drizzle.team/docs/migrations
- https://orm.drizzle.team/docs/rls
- https://orm.drizzle.team/docs/studio
