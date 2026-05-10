# Tech-Stack: TanStack Query

> [!NOTE]
> **TRIGGER:** LOAD ON API data fetching, caching, server state management.
> **SCOPE:** TanStack Query v5, Next.js hydration.

## 1. Query Patterns
- Use a Query Keys Factory pattern (e.g., `const keys = { all: ['users'], detail: (id) => [...keys.all, id] }`) to ensure type safety and consistency.
- Separate fetcher functions from components for testability.
- Utilize Stale-While-Revalidate (SWR) logic as the default caching mechanism.

## 2. Mutations & Updates
- Implement Optimistic Updates for highly interactive mutations to make the UI feel instant.
- Use `onSettled` in mutations to invalidate relevant query keys and trigger refetches.
- Define retry logic appropriately (e.g., disable retries for 4xx errors, retry 5xx).

## 3. Advanced Features
- Use Infinite Queries for cursor-based or offset-based pagination.
- Prefetch queries on server or on hover (using `queryClient.prefetchQuery`) to eliminate loading spinners.
- Handle SSR effectively by dehydrating state on the server and hydrating the `QueryClientProvider` in Next.js.
- Integrate with React Error Boundaries for robust error handling.

## 4. Hard Constraints
- NEVER mutate the cached data directly outside of `queryClient.setQueryData`.
- NEVER use generic string arrays as query keys without a central factory pattern.
- ALWAYS handle loading, error, and success states explicitly in the UI.

---

## ✅ TANSTACK QUERY COMPLIANCE CHECK (Mandatory)
- [ ] **Query Keys:** Is a central factory pattern used for all query keys?
- [ ] **Mutations:** Are queries properly invalidated after successful mutations?
- [ ] **Performance:** Is prefetching or optimistic updating utilized for better UX?
