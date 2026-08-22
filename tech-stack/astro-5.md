[TECH] Astro 5
[OBJ] Content-driven web framework with islands architecture, server islands, content collections, actions, and Astro DB.
[RULES]
1. [REQ] Use Content Collections for all structured content: define a schema in `src/content.config.ts` with Zod, then query with `getCollection("name")` — never read markdown / MDX directly from the filesystem.
2. [REQ] Use the Content Layer API (`loader()` in collection config) for external data sources (CMS, API, local files); custom loaders must implement `load()` returning an array of entries.
3. [REQ] Use islands architecture: set `client:load`, `client:idle`, `client:visible`, or `client:only` directives on interactive framework components — default is zero JS.
4. [REQ] Use server islands (`server:defer`) to defer non-critical server-rendered components so the main page streams immediately.
5. [REQ] Use Astro Actions (`src/actions/`) for type-safe form / API mutations: define with `defineAction({ input: zodSchema, handler })` and call from client with `fetch` to the action endpoint.
6. [REQ] Use middleware (`src/middleware.ts`) with `defineMiddleware` for request-level concerns (auth, locale, headers); use `locals` on `context` to pass data to pages.
7. [REQ] Use `astro:env` for typed environment variables: define schema in `astro.config.mjs` `env.schema` with `envField.string()` / `envField.secret()` — never access `process.env` directly.
8. [REQ] Use integrations (`@astrojs/react`, `@astrojs/vue`, `@astrojs/svelte`, `@astrojs/tailwind`) for framework components; register in `integrations: [...]` in config.
9. [REQ] Use Astro DB / Studio for embedded SQLite databases: define tables in `db/config.ts`, query with `db.select()` / `db.insert()`; use `@astrojs/db` integration.
10. [REQ] Use `getStaticPaths()` for dynamic routes in static mode; return an array of `{ params, props }` objects.
11. [REQ] Use `Astro.locals` and `Astro.request` for server-side data in pages; use `fetch` in frontmatter for SSR / hybrid pages.
12. [REQ] Use `astro check` for type checking and `astro dev` / `astro build` / `astro preview` CLI commands; run `astro check` in CI before build.
13. [REQ] Use output mode `static` (default), `server` (SSR), or `hybrid` (per-route) — set `output: "hybrid"` and `export const prerender = true/false` per page.
14. [PROHIBIT] Never ship JavaScript to pages that don't need interactivity — Astro's default is zero JS. Never use `client:only` when server rendering is possible (it skips SSR).
15. [PROHIBIT] Never bypass Content Collections by reading files with `fs.readFileSync` — always use the collection API for type safety and validation.
[COMPAT]
- v5.0: Content Layer API, server islands, Astro Actions, `astro:env`, Astro DB GA, Vite 6, Node.js 18.20+ / 20.3+ / 22+.
- v5.6: `experimental.svg` component, improved session API, live content collections.
[REFS]
- https://docs.astro.build/en/getting-started/
- https://docs.astro.build/en/guides/content-collections/
- https://docs.astro.build/en/guides/actions/
