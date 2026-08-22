[TECH] SolidJS 1.x
[OBJ] Fine-grained reactive UI framework with signals, no virtual DOM, JSX compilation, and SolidStart for full-stack apps.
[RULES]
1. [REQ] Use `createSignal()` for reactive primitives and `createMemo()` for derived values; signals are the only reactivity primitive — there is no virtual DOM diffing.
2. [REQ] Use `createEffect()` for side-effects that read signals; use `createRenderEffect()` for effects that must run before DOM commit; always return a cleanup function from effects.
3. [REQ] Use `createResource()` for async data fetching: `const [data] = createResource(fetcher)` — returns a signal with `loading`, `error`, and `state` properties.
4. [REQ] Use `createStore()` for fine-grained nested reactive objects; never use `createSignal` with a deeply nested object and replace the whole object on each change.
5. [REQ] Use `onMount()`, `onCleanup()`, `onError()` lifecycle functions; `onMount` is shorthand for `createEffect` that runs once.
6. [REQ] Use `Show`, `For`, `Switch` / `Match`, `Index`, `Dynamic`, and `Portal` control-flow components — never use `.map()` / `.filter()` directly in JSX (breaks reactivity).
7. [REQ] Use `props` as a proxy object — never destructure props (`const { title } = props`) as it breaks reactivity; access props lazily (`props.title`).
8. [REQ] Use `splitProps()` to separate reactive props into groups; use `mergeProps()` to combine defaults with incoming props.
9. [REQ] Use SolidStart for full-stack apps: define routes with file-based routing in `src/routes/`, server functions with `"use server"` directive, and `createServerData()` for SSR data.
10. [REQ] Use streaming SSR with `renderToStream()` for progressive hydration; use `Suspense` boundaries with `fallback` for async chunks.
11. [REQ] Use `use:` directive for ref-based actions (e.g., `use:intersectionObserver`); the directive function receives the element and accessor for value.
12. [REQ] Use `dev` / `build` from `solid-js` / Vite; configure `vite-plugin-solid` with `ssr: true` for SolidStart SSR.
13. [REQ] Use `@solidjs/testing-library` for component tests and `vitest` for unit tests; mock signals with `createRoot` in test setup.
14. [PROHIBIT] Never destructure props — it breaks reactivity. Never use `React.createElement` or React-specific patterns. Never use array `.map()` in JSX — use `<For>`.
15. [PROHIBIT] Never use `createEffect` for computing derived state — use `createMemo`. Never mutate signal values without calling the setter.
[COMPAT]
- v1.8: SolidStart 1, streaming SSR, `createAsync` / `query` for server functions.
- v1.9: Improved hydration, `use:` directive typing, SolidStart stable.
[REFS]
- https://www.solidjs.com/docs/latest
- https://start.solidjs.com/
- https://github.com/solidjs/solid-testing-library
