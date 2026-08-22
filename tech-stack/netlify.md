[TECH] netlify
[OBJ] Netlify platform — continuous deployment, functions, edge functions, redirects, forms, identity, large media, split testing.
[RULES]
1. [REQ] Use Git-connected continuous deployment; every push triggers a build and deploy — configure build settings (build command, publish directory) in `netlify.toml` or the Dashboard; never deploy via drag-and-drop for production workflows.
2. [REQ] Configure serverless functions in the `netlify/functions/` directory or via framework conventions (Next.js `/api`, etc.); functions use the V2 architecture with `export default` handler signature — set `maxDuration` in function frontmatter (up to 26s on free, 300s on Pro).
3. [REQ] Use Edge Functions via `netlify/edge-functions/` directory with Deno runtime; declare `export default async (request, context) => {}` — never use Node.js-specific APIs in Edge Functions; use `context.geo` and `context.cookies` for edge logic.
4. [REQ] Configure redirects and rewrites in `netlify.toml` or `_redirects` file; use `status` codes (301, 302, 200 for rewrites) and `force = true` to override static files — place SPA fallbacks (`/* /index.html 200`) last to avoid shadowing API routes.
5. [REQ] Use Netlify Forms for static form handling; add `data-netlify="true"` to HTML forms and handle submissions via the Forms API or notification emails — enable spam protection with `data-netlify-recaptcha="true"` and never accept form submissions without honeypot or reCAPTCHA.
6. [REQ] Use Netlify Identity for authentication via GoTrue; integrate with `netlify-identity-widget` or `gotrue-js` — configure external providers (Google, GitHub) in the Dashboard and handle JWT verification on serverless functions via `context.clientContext.user`.
7. [REQ] Configure Netlify Large Media for Git LFS-backed assets; use `netlify-large-media` CLI to track files — never commit large binaries directly to Git; use LFS for files >10MB and configure CDN caching headers for optimized delivery.
8. [REQ] Use split testing via Netlify's built-in A/B testing feature; configure branch-based splits in the Dashboard or `netlify.toml` — use `Set-Cookie: nf_ab=<variant>` to persist variant assignment and never run split tests without statistical significance thresholds.
9. [REQ] Set environment variables via the Dashboard or CLI (`netlify env:set`); scope variables to deploy contexts (production, deploy previews, branch deploys) — never commit secrets to `netlify.toml` or the repository.
10. [REQ] Handle build failures by checking Netlify build logs; common issues include missing env vars, incorrect publish directory, and function bundling errors — use `netlify build` locally with `--dry` to debug before pushing.
11. [PROHIBIT] Never store secrets in `netlify.toml` — use environment variables; never use Netlify Forms without spam protection; never disable deploy previews for PRs in production projects.
12. [PROHIBIT] Never exceed function timeout without configuring `maxDuration`; never use Edge Functions for database connections (use serverless functions with connection pooling); never bypass Netlify's CDN cache without explicit `Cache-Control` headers.
[COMPAT]
- Netlify Platform 2024: Functions V2 GA, Edge Functions (Deno) GA, Next.js 15 supported.
- Functions: Node.js 18/20/22, Go, Rust — up to 300s duration (Pro).
- Edge Functions: Deno runtime, 50ms global latency, no Node.js APIs.
[REFS]
- https://docs.netlify.com/
- https://docs.netlify.com/functions/overview/
- https://docs.netlify.com/edge-functions/overview/
- https://docs.netlify.com/routing/redirects/
- https://docs.netlify.com/forms/setup/
