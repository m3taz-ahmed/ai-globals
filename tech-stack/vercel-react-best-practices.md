[TECH] vercel-react-best-practices
[OBJ] Vercel React Best Practices (Performance).
[RULES]
1. [REQ] Waterfalls: Await late. `Promise.all()`. Suspense streaming.
2. [REQ] Bundles: Avoid barrel imports. Use `next/dynamic`. Defer third-party scripts.
3. [REQ] Server: Auth server actions. `React.cache()`. Restructure to parallelize fetches.
4. [REQ] Re-renders: Defer state reads. Move effect logic to events. `useDeferredValue`.
5. [REQ] Rendering: Hoist static JSX. Use ternary, not `&&`.
