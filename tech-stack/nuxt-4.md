[TECH] Nuxt 4
[OBJ] Full-stack Vue framework with auto-imports, Nitro server engine, layers, file-based routing, and SSR with hydration.
[RULES]
1. [REQ] Use the `app/` directory structure (Nuxt 4 default): `app/pages/`, `app/components/`, `app/composables/`, `app/layouts/`, `app/middleware/` — the root `srcDir` is now `app/`.
2. [REQ] Use auto-imports for composables and components — do not manually import `ref`, `computed`, `useFetch`, or components in `app/components/`; Nuxt auto-registers them.
3. [REQ] Use `useFetch()` / `useAsyncData()` for data fetching with automatic SSR serialization and hydration key deduplication; always provide a unique `key` when fetching the same endpoint with different params.
4. [REQ] Use `server/` directory for Nitro server routes: `server/api/users.get.ts` defines `GET /api/users`; use `defineEventHandler()` and `readBody()` for input.
5. [REQ] Use Nitro as the server engine: deploy presets for Vercel, Netlify, Cloudflare, Node, or Docker via `NITRO_PRESET` env var; never run the dev server in production.
6. [REQ] Use layers for multi-project code sharing: define `nuxt.config.ts` `extends: ["../base-layer"]`; each layer can contribute pages, components, composables, and server routes.
7. [REQ] Use `useState()` for shared reactive state across components with SSR-safe hydration; never use module-level `ref()` for shared state (breaks SSR).
8. [REQ] Use route middleware (`app/middleware/auth.ts`) with `defineNuxtRouteMiddleware()`; apply globally via `nuxt.config` `router.middleware` or per-page with `definePageMeta({ middleware: ["auth"] })`.
9. [REQ] Use `definePageMeta()` for page-level configuration (`layout`, `middleware`, `keepalive`, `alias`); use `<NuxtLayout>` for layout slots.
10. [REQ] Use `useRuntimeConfig()` for environment variables: define `runtimeConfig` in `nuxt.config.ts` with `public` / private split; access private keys only on server.
11. [REQ] Use `app.vue` as the root component with `<NuxtPage />` and `<NuxtLayout>`; use `error.vue` for global error page.
12. [REQ] Use `nuxt build` / `nuxt preview` for production; use `nuxt dev` for development with HMR; run `nuxi typecheck` in CI for TypeScript validation.
13. [REQ] Use Pinia for complex state management (`@pinia/nuxt` module auto-imports `defineStore`); use `useState` for simple shared refs.
14. [PROHIBIT] Never use `process.env` directly in client code — use `useRuntimeConfig().public`. Never disable SSR (`ssr: false`) without a documented reason.
15. [PROHIBIT] Never use `window` / `document` in setup top-level code — guard with `import.meta.client` or use `onMounted`. Never fetch data in `onMounted` — use `useFetch` for SSR.
[COMPAT]
- v4.0: `app/` directory default, Vue 3.5+, Nitro 2.x, Vite 6, new data fetching defaults, TypeScript 5.7+, Node 18+.
- v4.1+: Improved layers merging, `useId()` SSR-safe, `defineModel` in Nuxt components.
[REFS]
- https://nuxt.com/docs
- https://nuxt.com/docs/guide/directory-structure/app
- https://nitro.unjs.io/
