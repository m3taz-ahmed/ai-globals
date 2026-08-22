[TECH] Remix 2
[OBJ] Full-stack web framework with nested routes, loaders, actions, error boundaries, and Vite-powered builds.
[RULES]
1. [REQ] Use file-based routing in `app/routes/`: `loader` for GET data fetching, `action` for POST / PUT / DELETE mutations — both run on the server and are type-safe with `typedResponse`.
2. [REQ] Use nested routes with `Outlet` for layout composition; each parent route's `loader` runs in parallel with child loaders — never waterfall data fetching across nested routes.
3. [REQ] Use `json()` / `defer()` helpers to return typed responses from loaders; use `defer()` with promises to stream slow data while sending critical data immediately.
4. [REQ] Use `useLoaderData()` / `useActionData()` in components; use `Await` component with `resolve` prop to render deferred data with a `#fallback` slot.
5. [REQ] Use error boundaries: export `ErrorBoundary` from any route to catch errors thrown in `loader`, `action`, or component for that route segment — never let errors bubble to the root without a boundary.
6. [REQ] Use `useFetcher()` for mutations without navigation (optimistic UI, forms in sidebars) and `useNavigation()` for global navigation state (`idle`, `submitting`, `loading`).
7. [REQ] Use `meta()` export function (not `MetaFunction` type) for route metadata in v2; access data via `matches` parameter for nested route meta merging.
8. [REQ] Use `headers()` export to control `Cache-Control` / `Vary` per route; use `Cache-Control: public, max-age=300, s-maxage=600` for cacheable pages.
9. [REQ] Use `@remix-run/node` `createCookie()` / `createCookieSessionStorage()` for sessions; never store secrets client-side; set `httpOnly`, `secure`, `sameSite: "lax"`.
10. [REQ] Use Vite as the build tool (`@remix-run/dev` Vite plugin); configure `vite.config.ts` with `remix({})` plugin and use `vite` / `vite build` commands.
11. [REQ] Use SPA mode (`ssr: false` in `remix.config` or `export const ssr = false` in root) only for apps that cannot run a server; otherwise prefer SSR for SEO and performance.
12. [REQ] Use `unstable_singleFetch` (v2.9+) or `unstable_data` for fine-grained data fetching; migrate to single-fetch for v3 readiness.
13. [REQ] Validate all form / action input with Zod or Valibot; parse `formData` with `Object.fromEntries()` then validate against schema.
14. [PROHIBIT] Never use `useEffect` + `fetch` for initial data loading — use `loader` + `useLoaderData`. Never call `loader` functions from client code.
15. [PROHIBIT] Never throw `Response` objects with unvalidated user data in error messages. Never disable error boundaries in production.
[COMPAT]
- v2.0: Vite plugin stable, `meta()` function, `future` flags removed, Node 18+.
- v2.9+: Single fetch (opt-in), `unstable_data`, React Router v7 merge path announced.
- v2.15+: SPA mode stable, `Route.Component` API (React Router v7 bridge).
[REFS]
- https://remix.run/docs/en/main
- https://remix.run/docs/en/main/guides/vite
- https://remix.run/docs/en/main/route/error-boundary
