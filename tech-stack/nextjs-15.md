# Tech-Stack: Next.js 15

> [!NOTE]
> **TRIGGER:** LOAD ON frontend tasks, React development, page creation, UI updates.
> **SCOPE:** Next.js 15 App Router, React 19 features, Server Components.

## 1. Server Components & Actions
- Default to React Server Components (RSC). Only use `'use client'` when state, lifecycle hooks, or browser APIs are required.
- Use Server Actions for data mutations instead of API routes where possible. Ensure actions validate input using Zod.
- Pass plain objects or simple primitives from Server Components to Client Components to avoid serialization errors.

## 2. Routing & Data Fetching
- Use Parallel Routes (`@folder`) for independent UI areas (e.g., sidebars, modals).
- Use Intercepting Routes (`(..)folder`) for contextual views like feed image modals.
- Leverage `fetch` with Next.js extended options (`next: { revalidate: 3600 }`) for Incremental Static Regeneration (ISR).
- Implement streaming using `loading.tsx` and React `<Suspense>` boundaries to improve Time to First Byte (TTFB).

## 3. Optimizations & APIs
- ALWAYS use `next/image` for image optimization (WebP/AVIF formats).
- ALWAYS use `next/font` for local font hosting to prevent cumulative layout shift (CLS).
- Define metadata using the Metadata API (`generateMetadata` or static `metadata` exports) for SEO.
- Handle runtime exceptions gracefully with `error.tsx` and `global-error.tsx`.

## 4. Hard Constraints
- NEVER use the Pages Router (`pages/`) in this project.
- NEVER fetch sensitive data in Client Components without proper API security.
- ALWAYS wrap Server Actions in try/catch blocks and handle authorization before execution.

---

## ✅ NEXT.JS 15 COMPLIANCE CHECK (Mandatory)
- [ ] **Component Paradigm:** Are Server Components the default, and is `'use client'` justified?
- [ ] **Data Mutation:** Are Server Actions used with proper Zod validation and authorization?
- [ ] **Performance:** Are `next/image` and `next/font` utilized, and are loading states managed with Suspense?
