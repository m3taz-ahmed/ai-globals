[TECH] cloudflare-pages
[OBJ] Cloudflare Pages — Git integration, functions, redirects, headers, environment variables, D1, R2, KV.
[RULES]
1. [REQ] Use Git-connected deployments via Cloudflare Pages Git integration; every push triggers a build and deploy — configure build command, output directory, and root directory in the Pages project settings or `wrangler.toml`.
2. [REQ] Configure Pages Functions in the `functions/` directory with file-based routing; functions run on the Cloudflare Workers runtime (V8 isolates) — use `export async function onRequestGet(context)` pattern and access bindings via `context.env`.
3. [REQ] Use `_redirects` file for redirects and rewrites; format: `<source> <destination> <status>` — use `200` for rewrites (SPA fallback) and `301`/`302` for redirects; place specific rules before catch-all `/*` rules.
4. [REQ] Use `_headers` file for custom HTTP headers; format: `URL\n  Header-Name: value` — set `Strict-Transport-Security`, `Content-Security-Policy`, and `X-Frame-Options` for security; never use wildcard CORS (`Access-Control-Allow-Origin: *`) for authenticated APIs.
5. [REQ] Set environment variables via the Cloudflare Dashboard or Wrangler CLI (`wrangler pages secret put`); distinguish between plaintext env vars (build-time) and encrypted secrets (runtime) — never commit secrets to the repository or `_headers` file.
6. [REQ] Bind D1 (SQLite database) to Pages Functions via `[[d1_databases]]` in `wrangler.toml`; access via `context.env.DB` — use prepared statements with parameterized queries to prevent SQL injection; never use string concatenation for SQL.
7. [REQ] Bind R2 (S3-compatible object storage) to Pages Functions via `[[r2_buckets]]` in `wrangler.toml`; access via `context.env.BUCKET` — use `put()`, `get()`, and `delete()` methods; set `Cache-Control` headers on R2 objects for CDN caching.
8. [REQ] Bind KV (key-value store) to Pages Functions via `[[kv_namespaces]]` in `wrangler.toml`; access via `context.env.KV` — use `get()` and `put()` with `expirationTtl` for time-based expiry; never store sensitive data in KV without encryption (KV is eventually consistent).
9. [REQ] Use `wrangler pages dev` for local development with bindings; start the dev server with `--local` flag to use local D1/R2/KV emulators — never develop against production bindings directly.
10. [REQ] Handle function errors with try/catch and return appropriate `Response` objects with status codes; log errors via `console.log` (visible in Cloudflare Dashboard > Functions > Logs) — never expose stack traces in production responses.
11. [PROHIBIT] Never store secrets in `wrangler.toml` — use `wrangler pages secret put`; never use Node.js-specific APIs in Pages Functions (Workers runtime only); never bypass the `_headers` security headers.
12. [PROHIBIT] Never exceed the Workers CPU time limit (10ms free, 50ms paid for Pages Functions); never use D1 for high-write workloads (D1 is optimized for reads); never store PII in KV without encryption.
[COMPAT]
- Cloudflare Pages 2024: Functions GA, Wrangler v3.x, D1 GA, R2 GA, KV GA.
- Functions: Workers runtime (V8 isolates), Node.js compat mode available via `nodejs_compat` flag.
- Frameworks: Next.js (via `@cloudflare/next-on-pages`), Astro, Nuxt, SvelteKit, Remix.
[REFS]
- https://developers.cloudflare.com/pages/
- https://developers.cloudflare.com/pages/functions/
- https://developers.cloudflare.com/pages/configuration/redirects/
- https://developers.cloudflare.com/d1/
- https://developers.cloudflare.com/r2/
