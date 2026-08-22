[TECH] supabase
[OBJ] Supabase platform — Postgres, Auth, Storage, Edge Functions, Realtime, Row Level Security, pgvector, migrations, Studio.
[RULES]
1. [REQ] Use the Supabase JavaScript/TypeScript SDK (`@supabase/supabase-js`) for client and server integration; initialize with `createClient(url, anonKey)` on the client and `createClient(url, serviceRoleKey)` on the server — never expose the `service_role` key to the client.
2. [REQ] Enable Row Level Security (RLS) on all tables; create policies using `create policy` with `using` (read) and `with check` (write) clauses — never disable RLS on tables accessible via the anon key; use the `service_role` key only for admin operations that bypass RLS.
3. [REQ] Use Supabase Auth for authentication; configure email/password, OAuth providers (Google, GitHub, Apple, etc.), and magic links via the Dashboard — map auth users to your data via `auth.uid()` in RLS policies; never implement custom auth outside Supabase Auth.
4. [REQ] Use Supabase Storage for file uploads; create public and private buckets via the Dashboard or API — upload via `supabase.storage.from('bucket').upload(path, file)` and generate signed URLs for private files; never make private buckets public.
5. [REQ] Use Edge Functions (Deno runtime) for server-side logic; deploy via `supabase functions deploy <name>` and serve at `https://<project>.functions.supabase.co/<name>` — verify the `Authorization: Bearer <jwt>` header using `supabase.auth.getUser()` inside the function; never use Node.js APIs in Edge Functions.
6. [REQ] Use Supabase Realtime for live updates; subscribe to Postgres changes via `supabase.channel('name').on('postgres_changes', { event, schema, table }, callback)` — enable Realtime on tables via `alter publication supabase_realtime add table <table>`; never expose Realtime without RLS policies (Realtime respects RLS).
7. [REQ] Use pgvector for AI/embedding workloads; enable via `create extension vector` and store embeddings in `vector(1536)` columns — use `<=>` (cosine distance) or `<->` (L2 distance) operators for similarity search; create an HNSW index for large datasets (`create index on <table> using hnsw (<column> vector_cosine_ops)`).
8. [REQ] Use Supabase Migrations for schema management; create migrations via `supabase migration new <name>` and apply with `supabase db push` — never apply schema changes directly via the SQL Editor in production; use the migration workflow for all schema changes.
9. [REQ] Use Supabase Studio for database management and monitoring; access via the Dashboard or self-hosted Studio — use the Table Editor for data CRUD, SQL Editor for ad-hoc queries, and Database > Reports for performance monitoring; never use Studio for production schema migrations (use CLI).
10. [REQ] Configure database backups via the Dashboard; Supabase Pro and above include daily backups and Point-in-Time Recovery (PITR) — test restore procedures regularly and never rely solely on application-level backups.
11. [PROHIBIT] Never expose the `service_role` key in client-side code or public repositories; never disable RLS on tables accessible via the anon key; never use the SQL Editor for production schema migrations.
12. [PROHIBIT] Never store PII in public Storage buckets; never use Edge Functions for long-running operations (>150s timeout); never bypass Supabase Auth for user authentication in production.
[COMPAT]
- Supabase Platform 2024: Postgres 15/16, pgvector 0.7.x, Edge Functions (Deno 1.x), Realtime v2.
- SDK: `@supabase/supabase-js` v2.x, `@supabase/ssr` for Next.js/SSR frameworks.
- CLI: `supabase` v1.x (local development, migrations, functions deploy).
[REFS]
- https://supabase.com/docs
- https://supabase.com/docs/guides/auth
- https://supabase.com/docs/guides/database/row-level-security
- https://supabase.com/docs/guides/ai/vector-columns
- https://supabase.com/docs/guides/functions
