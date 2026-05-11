# Tech-Stack: Next.js 15

> [!NOTE]
> **TRIGGER:** LOAD ON frontend tasks, React development, page creation, UI updates.
> **SCOPE:** Next.js 15 App Router, React 19 features, Server Components, Partial Prerendering.

## 1. Server Components & Actions
- Default to React Server Components (RSC). Only use `'use client'` when state, lifecycle hooks, or browser APIs are required.
- Use Server Actions for data mutations instead of API routes where possible. Ensure actions validate input using Zod (ref: `zod-validation.md`).
- Pass plain objects or simple primitives from Server Components to Client Components to avoid serialization errors.
- **React Compiler:** Fully rely on the stable React Compiler. Eliminate manual `useMemo` and `useCallback` hooks to prevent code bloat.
- Use React 19's `use()` hook to unwrap promises and contexts in Server Components for cleaner async data flow.

## 2. Partial Prerendering (PPR)
- Enable PPR (`experimental.ppr = 'incremental'` in `next.config.ts`) to serve a static shell with dynamic holes, combining SPA-like interactivity with SSR-level performance.
- Mark dynamic regions with `<Suspense>` boundaries; Next.js streams the static shell instantly and fills dynamic holes asynchronously.
- Design pages with a clear static/dynamic split: navigation, layout, and chrome are static; user-specific panels, feeds, and personalized sections are dynamic.

## 3. Routing & Data Fetching
- Use Parallel Routes (`@folder`) for independent UI areas (e.g., sidebars, modals).
- Use Intercepting Routes (`(..)folder`) for contextual views like feed image modals.
- **Explicit Caching:** Abandon implicit fetch caching. Use the explicit `"use cache"` directive for functions and components to generate predictable cache keys (Next.js 15/16 standard).
- Implement streaming using `loading.tsx` and React `<Suspense>` boundaries to improve Time to First Byte (TTFB).
- Use the `after()` API for post-response work (analytics, logging, cache revalidation) that does not block the user response.

## 4. Turbopack & Build
- Use Turbopack (`next dev --turbopack`) as the default dev server (stable in Next.js 15) for up to 96% faster local development compared to Webpack.
- Configure `next.config.ts` (TypeScript config) instead of `next.config.mjs` for full type safety and autocompletion.
- Use `dynamicIO` config to explicitly declare dynamic I/O boundaries and catch accidental dynamic renders during development.

## 5. Optimizations & APIs
- ALWAYS use `next/image` for image optimization (WebP/AVIF formats).
- ALWAYS use `next/font` for local font hosting to prevent cumulative layout shift (CLS).
- Define metadata using the Metadata API (`generateMetadata` or static `metadata` exports) for SEO.
- Handle runtime exceptions gracefully with `error.tsx` and `global-error.tsx`.

## 6. Hard Constraints
- NEVER use the Pages Router (`pages/`) in this project.
- NEVER fetch sensitive data in Client Components without proper API security.
- ALWAYS wrap Server Actions in try/catch blocks and handle authorization before execution.
- NEVER use `next.config.mjs` or `next.config.js`; use `next.config.ts` for type safety.

---

## ✅ NEXT.JS 15 COMPLIANCE CHECK (Mandatory)
- [ ] **Component Paradigm:** Are Server Components the default, and is `'use client'` justified?
- [ ] **Data Mutation:** Are Server Actions used with proper Zod validation and authorization?
- [ ] **Performance:** Are `next/image` and `next/font` utilized, and are loading states managed with Suspense?
- [ ] **PPR:** Is Partial Prerendering enabled with clear static/dynamic boundaries?
- [ ] **Build Tooling:** Is Turbopack used in dev and `next.config.ts` used for configuration?
