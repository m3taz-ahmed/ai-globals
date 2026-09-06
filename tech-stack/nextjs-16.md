[TECH] Next.js 16
[OBJ] React 19.2+ full-stack framework. Cache Components (PPR + `use cache`), Proxy.ts replacing middleware, SPA-like navigations, Turbopack default, Devtools MCP, AI tooling.
[RULES]
1. [REQ] Use Turbopack as default bundler for dev + prod (`next dev` / `next build`); Webpack is opt-in only via `--webpack` flag.
2. [REQ] Use Cache Components: enable PPR (Partial Prerendering) + `"use cache"` directive for instant navigation. Mark dynamic components with `connection()`; static shell prerenders at build.
3. [REQ] Replace `middleware.ts` with `proxy.ts` for network-boundary logic (auth, redirects, rewrites). Proxy runs on the edge; clarify what executes server-side vs edge.
4. [REQ] Use SPA-like navigations: client-side route transitions with cached data; prefetch route segments on hover/viewport.
5. [REQ] React 19.2+ required: use `use()`, Server Actions, `useFormState` / `useFormStatus`, `useOptimistic`. No React 18 patterns.
6. [REQ] Use App Router (`app/` dir) with Server Components by default. Mark client components with `"use client"` only when interactivity needed.
7. [REQ] Use `next/cache` APIs: `unstable_cache`, `revalidateTag`, `revalidatePath`. With Cache Components, prefer `"use cache"` + `cacheTag` / `cacheLife`.
8. [REQ] Integrate Next.js Devtools MCP for debugging: exposes route tree, cache state, render output via Model Context Protocol.
9. [REQ] Use AI tooling: `AGENTS.md` scaffolded by `create-next-app`, browser log forwarding (console → dev server terminal), `next-browser` experimental for agent-driven browser interaction.
10. [REQ] Use Server Actions for mutations; validate inputs with Zod / Valibot. Never trust client input.
11. [REQ] Use `next/image` for all images with `width`/`height` or `fill`. Configure `remotePatterns` in `next.config.ts`.
12. [REQ] Use `next/font` (Google / local fonts) with CSS variables. No `@font-face` manual setup.
13. [REQ] Configure metadata via `metadata` export or `generateMetadata()`; use `viewport` export separately.
14. [REQ] Lower dev-server memory: streaming SSR + incremental cache reduces footprint ~40% vs v15.
15. [REQ] Faster rendering: ~50% improvement via React Compiler + Turbopack optimizations.
16. [CMD] `npx create-next-app@latest` scaffolds new app with `AGENTS.md` + Turbopack defaults.
17. [CMD] `next dev --turbopack` explicit Turbopack dev (default but explicit for CI).
18. [CMD] `next build --turbopack` production build with Turbopack.
19. [PROHIBIT] Never use `middleware.ts` for new Next 16 projects — migrate to `proxy.ts`.
20. [PROHIBIT] Never use `getServerSideProps` / `getStaticProps` (Pages Router legacy) in new App Router code.
21. [PROHIBIT] Never disable React Compiler (`reactCompiler: false`) without documented reason.
22. [PROHIBIT] Never use `next export` — replaced by `output: "export"` in config.
[COMPAT]
- Next.js 16.x (released Oct 2025, latest 16.3.4 Aug 2026).
- React 19.2+ required.
- Turbopack default (Webpack opt-in).
- Node.js 20.9+ minimum, 22+ recommended.
- Next.js 15 EOL Oct 2026 — migrate before deadline.
- TypeScript 5.6+ (TS 6.0 compatible).
[REFS]
- https://nextjs.org/docs
- https://nextjs.org/docs/app/api-reference/functions/use-cache
- https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- https://next.dev/blog/next-16
