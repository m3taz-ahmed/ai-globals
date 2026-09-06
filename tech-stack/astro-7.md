[TECH] Astro 7 (latest 7.3.1, Sep 2026)
[OBJ] Content-driven web framework — pluggable Markdown pipeline, Rust-based Markdown processor, Cloudflare advanced routing helpers, Fonts API, CSP API, live content collections.
[RULES]
1. [REQ] Use pluggable Markdown pipeline — configure processors via `astro.config.mjs` `markdown` options; replace legacy `remarkPlugins`/`rehypePlugins` arrays with pipeline plugins.
2. [REQ] Use Rust-based Markdown processor for performance — enabled by default; fallback to JS processor via config if custom plugins require it.
3. [REQ] Use Cloudflare advanced routing helpers for CF Pages deployments — `getCloudflareContext()`, advanced routing config in `astro.config.mjs`.
4. [REQ] Use Fonts API (`experimental.fonts` → stable in v7) — define font families in `astro.config.mjs` instead of manual `@font-face` CSS.
5. [REQ] Use CSP API (`astro:middleware` + CSP headers) — configure Content-Security-Policy via `csp` option in config.
6. [REQ] Use live content collections for real-time data — `live` collections sync from external APIs/CMS with type safety.
7. [REQ] Use content collections (`src/content/`) with `defineCollection()` + Zod schema for structured content.
8. [REQ] Use `getStaticPaths()` for dynamic routes in static builds; use server islands for partial hydration.
9. [REQ] Use `Astro.locals` for middleware-injected context; never mutate `Astro.request` directly.
10. [REQ] Use integrations (`@astrojs/react`, `@astrojs/vue`, etc.) for framework components; isolate interactive islands with `client:*` directives.
11. [REQ] Use `astro:content` / `astro:assets` / `astro:env` virtual modules for typed access.
12. [REQ] Use View Transitions API (`<ViewTransitions />`) for SPA-like navigation in MPA architecture.
13. [PROHIBIT] Never use legacy Markdown config format — migrate to pluggable pipeline API.
14. [PROHIBIT] Never hardcode `@font-face` in CSS — use Fonts API.
15. [PROHIBIT] Never set CSP headers manually in middleware — use CSP API.
16. [PROHIBIT] Never use `client:only` without a fallback for SSR-rendered content.
17. [CMD] `npm create astro@latest` — scaffold new project.
18. [CMD] `astro build` — production build.
19. [CMD] `astro dev` — dev server.
20. [CMD] `astro check` — type-check + diagnostics.
[COMPAT]
- v7.0+: Pluggable Markdown pipeline, Rust Markdown processor, Cloudflare advanced routing.
- v6 (prior): Fonts API, CSP API, live content collections introduced.
- v7.3.1: latest stable patch.
- Node v20.19+ / v22.12+ recommended.
[REFS]
- https://docs.astro.build/
- https://docs.astro.build/en/guides/markdown/
- https://docs.astro.build/en/guides/fonts/
- https://docs.astro.build/en/guides/csp/
- https://docs.astro.build/en/guides/cloudflare/
