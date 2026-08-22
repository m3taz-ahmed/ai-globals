[TECH] vercel
[OBJ] Vercel platform — deployments, preview deployments, edge functions, serverless functions, ISR, OG image, Vercel Analytics, Cron.
[RULES]
1. [REQ] Use Git-connected deployments for automatic CI/CD; every push to a branch creates a preview deployment and merges to `main` trigger production deployments — never deploy via CLI (`vercel --prod`) for routine releases in Git-connected projects.
2. [REQ] Configure serverless functions in `/api` directory with framework-specific conventions (Next.js App Router uses `route.ts`, Pages Router uses `/api/*.ts`); set `maxDuration` per route (up to 300s on Pro/Enterprise) — never exceed the platform default timeout without explicit configuration.
3. [REQ] Use Edge Functions (Edge Runtime) for low-latency geolocation, A/B testing, and auth checks; set `export const runtime = 'edge'` in route handlers — never use Node.js-specific APIs (`fs`, `crypto.randomBytes`) in Edge Runtime.
4. [REQ] Configure ISR (Incremental Static Regeneration) via `revalidate` in `generateStaticParams` or `getStaticProps`; set `revalidate: <seconds>` for time-based revalidation and use `revalidatePath()` / `revalidateTag()` for on-demand revalidation via webhooks.
5. [REQ] Use `@vercel/og` for dynamic Open Graph image generation; create `opengraph-image.tsx` in App Router routes — never generate OG images at runtime without caching; use `export const runtime = 'edge'` for sub-50ms generation.
6. [REQ] Enable Vercel Analytics via `@vercel/analytics` package; inject `<Analytics />` component in the root layout — use Speed Insights (`@vercel/speed-insights`) for Core Web Vitals tracking; never use third-party analytics that block rendering.
7. [REQ] Configure Vercel Cron Jobs via `vercel.json` with `crons` array; each cron has `path` and `schedule` (crontab syntax) — the cron endpoint must be a serverless function that verifies the `CRON_SECRET` env var to prevent unauthorized invocation.
8. [REQ] Set environment variables via the Vercel Dashboard or CLI (`vercel env add`); mark secrets as `Encrypted` and assign to correct environments (Production, Preview, Development) — never commit `.env` files to the repository.
9. [REQ] Use Vercel's built-in image optimization via `next/image` with the Vercel image optimizer; configure `remotePatterns` for external image sources — never serve unoptimized images in production.
10. [REQ] Handle deployment failures by checking the Vercel build logs; common issues include missing env vars, framework misconfiguration, and function size limits (50MB unzipped for serverless, 4MB for edge) — use `vercel inspect` for debugging.
11. [PROHIBIT] Never store secrets in `vercel.json` — use environment variables; never use `vercel dev` as a production server; never disable preview deployments for PRs in production projects.
12. [PROHIBIT] Never exceed function concurrency limits without configuring `maxConcurrency`; never use Edge Functions for long-running operations (>30s); never bypass Vercel's CDN cache headers without explicit `Cache-Control` configuration.
[COMPAT]
- Vercel Platform 2024: Next.js 15 supported, Edge Runtime GA, Cron Jobs GA.
- Serverless Functions: Node.js 20/22, Python, Go, Ruby — up to 300s duration (Pro).
- Edge Functions: V8 isolate runtime, 30s max duration, no Node.js APIs.
[REFS]
- https://vercel.com/docs
- https://vercel.com/docs/functions/serverless-functions
- https://vercel.com/docs/functions/edge-functions
- https://vercel.com/docs/cron-jobs
- https://vercel.com/docs/analytics
