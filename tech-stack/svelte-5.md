[TECH] Svelte 5
[OBJ] Compiler-based UI framework with runes reactivity (`$state`, `$derived`, `$effect`), snippets, and SvelteKit for full-stack apps.
[RULES]
1. [REQ] Use runes for all reactivity: `$state()` for mutable state, `$derived()` for computed values, `$effect()` for side-effects — never use Svelte 4 `let` / `$:` reactivity in new code.
2. [REQ] Use `$state.raw()` for large immutable data that does not need deep reactivity (API responses, config objects) to avoid proxy overhead.
3. [REQ] Use `$effect.pre()` for pre-DOM-update side-effects and `$effect` for post-DOM; always return a cleanup function when subscribing to external stores.
4. [REQ] Use `$props()` in components: `let { title, count = 0, onAction } = $props()` — replaces Svelte 4 `export let`.
5. [REQ] Use snippets (`{#snippet name(props)}...{/snippet}`) for reusable markup within a component; use `{@render name(args)}` to invoke.
6. [REQ] Use SvelteKit `+page.server.ts` / `+layout.server.ts` `load` functions for server-side data fetching; use `+page.ts` for client-side or universal loads.
7. [REQ] Use SvelteKit `form` actions (`+page.server.ts` `actions`) for mutations with progressive enhancement; validate with a schema library (Zod / Valibot).
8. [REQ] Use `export const prerender = true` for static pages and `export const ssr = false` only for pages that genuinely require client-only rendering.
9. [REQ] Use `export const load` with `depends()` to tag fetch dependencies for fine-grained cache invalidation via `invalidate()`.
10. [REQ] Use `use:action` directives for DOM-level side-effects (intersection observer, focus trap, tooltip); return a `destroy` function for cleanup.
11. [REQ] Use `$host()` in custom elements (Svelte component compiled as web component) to access the host element.
12. [REQ] Use `svelte-check` for type checking and `vitest` with `@testing-library/svelte` for unit tests; run `svelte-check --tsconfig ./tsconfig.json` in CI.
13. [REQ] Use `setContext()` / `getContext()` for scoped dependency injection; type the context key with a `Symbol` and generic.
14. [PROHIBIT] Never mix Svelte 4 `export let` / `$:` / `on:click` with Svelte 5 runes in the same component — migrate fully. Never mutate `$derived` values.
15. [PROHIBIT] Never use `{@html}` with untrusted input — sanitize with DOMPurify. Never use `await` in `$derived` — use `$effect` or async stores.
[COMPAT]
- v5.0: Runes (`$state`, `$derived`, `$effect`, `$props`), snippets, event handlers as props (`onclick` not `on:click`), SvelteKit 2.
- v5.20+: `$state.snapshot`, improved async SSR, `mount()` / `hydrate()` API.
[REFS]
- https://svelte.dev/docs/svelte/what-are-runes
- https://svelte.dev/docs/kit/
- https://svelte.dev/docs/svelte/$state
