[TECH] nextjs-15
[OBJ] Next.js 15 App Router & React 19.
[RULES]
1. [REQ] RSC First: Default to Server Components. `'use client'` only for state/hooks/APIs.
2. [REQ] Server Actions: Use for data mutations + Zod validation. Try/Catch + Auth wrapper.
3. [REQ] React 19: Use React Compiler (no `useMemo`/`useCallback`). Use `use()` for async flow.
4. [REQ] PPR: Enable Partial Prerendering. Use `<Suspense>` for dynamic holes.
5. [REQ] Routing: Parallel `@folder` / Intercepting `(..)folder` routes. Explicit `"use cache"`. `after()` for non-blocking work.
6. [REQ] Build: Turbopack for dev. `next.config.ts`. `dynamicIO`. Use `next/image` and `next/font`.
7. [PROHIBIT] Constraints: NEVER use `pages/`. NEVER fetch sensitive data in Client Comps.
