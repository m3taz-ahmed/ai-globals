[TECH] nextjs-15
[OBJ] Next.js 15.2+ App Router, React 19, Partial Prerendering, caching changes, after() API, dynamicIO, useLinkStatus.
[RULES]
1. [REQ] RSC First: Default to Server Components. `'use client'` only for state/hooks/APIs.
2. [REQ] Server Actions: Use for data mutations + Zod validation. Try/Catch + Auth wrapper.
3. [REQ] React 19: Use React Compiler (no `useMemo`/`useCallback`). Use `use()` for async flow.
4. [REQ] PPR (Partial Prerendering): Enable via `experimental.ppr = true` in `next.config.ts`. Wrap dynamic content in `<Suspense>`. Static shell renders instantly; dynamic holes stream in. Use `connection()` to opt specific components into dynamic rendering within PPR pages.
5. [REQ] Routing: Parallel `@folder` / Intercepting `(..)folder` routes. Explicit `"use cache"` directive on cacheable functions. `after()` for non-blocking work (analytics, logging, webhooks) that runs after the response is sent.
6. [REQ] Build: Turbopack for dev (`next dev --turbopack`). `next.config.ts` (TypeScript config). `dynamicIO` flag. Use `next/image` and `next/font`.
7. [REQ] Caching (Next.js 15.2+): `fetch()` is no longer cached by default. Use `cache: 'force-cache'` for explicit caching. `revalidateTag()` and `revalidatePath()` for on-demand revalidation. `"use cache"` directive with `cacheTag()` and `cacheLife()` for fine-grained cache control.
8. [REQ] `after()` API: use `after(() => { ... })` for non-critical post-response work. Runs after the response is sent to the client. Use for analytics, logging, webhook dispatch, email sending. Never use `after()` for work that affects the response — it cannot modify the response after it's sent.
9. [REQ] `dynamicIO` flag: set `experimental.dynamicIO = true` in `next.config.ts` to enable `"use cache"` and `after()` APIs. Requires all I/O to be explicitly cached or marked dynamic. Enforces cache/dynamic boundaries at build time.
10. [REQ] `useLinkStatus()` hook: use `const { pending } = useLinkStatus()` inside `<Link>` children to show loading states during prefetch/navigation. Requires `<Link>` to render the hook consumer as a descendant. Use for navigation progress indicators and skeleton states.
11. [REQ] `connection()` function: call `await connection()` in a Server Component to opt it into dynamic rendering within a PPR page. Use sparingly — only for components that truly need per-request data. The rest of the page stays static.
12. [REQ] `"use cache"` directive: mark functions for caching with `"use cache"` at the top of the function body. Use `cacheTag("products")` for tag-based invalidation and `cacheLife("hours")` for TTL-based expiration. Configure cache profiles in `next.config.ts` under `experimental.cacheLife`.
13. [REQ] `next.config.ts`: use TypeScript config file instead of `next.config.js` / `next.config.mjs`. Provides type safety for config options. Import `type { NextConfig } from "next"`.
14. [REQ] Turbopack: use `next dev --turbopack` for development (10x faster HMR). Use `next build --turbopack` for production builds (stable in 15.2+). Webpack is still available as fallback but Turbopack is the default for new projects.
15. [REQ] Route Handlers: use `export const dynamic = "force-dynamic"` for always-dynamic routes. Use `export const revalidate = 0` to disable caching. Use `export const fetchCache = "default-no-store"` for opt-out of default fetch caching.
16. [PROHIBIT] NEVER use `pages/` directory. App Router (`app/`) is the only supported routing model for new projects.
17. [PROHIBIT] NEVER fetch sensitive data in Client Components. Use Server Components or Server Actions for authenticated data access.
18. [PROHIBIT] NEVER use `after()` for response-critical work. It runs after the response is sent and cannot modify it.
19. [PROHIBIT] NEVER rely on implicit `fetch()` caching (removed in 15.2+). Always specify `cache` option or use `"use cache"` directive.
[COMPAT]
- v15.2+: PPR (experimental), `after()` API, `dynamicIO`, `useLinkStatus()`, `connection()`, `"use cache"` directive, Turbopack production builds, `next.config.ts`.
- v15.0: App Router, React 19, Server Actions (stable), `fetch()` caching disabled by default.
- React 19: React Compiler, `use()` hook, `useFormState`, `useFormStatus`, `useOptimistic`.
- Build: Turbopack (default), Webpack (fallback).
[REFS]
- https://nextjs.org/docs
- https://nextjs.org/docs/app/building-your-application/rendering/partial-prerendering
- https://nextjs.org/docs/app/api-reference/functions/after
- https://nextjs.org/docs/app/api-reference/directives/use-cache
- https://nextjs.org/docs/app/api-reference/functions/use-link-status
- https://nextjs.org/blog/next-15-2
