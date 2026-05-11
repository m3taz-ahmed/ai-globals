# Tech-Stack: TanStack Query

> [!NOTE]
> **TRIGGER:** LOAD ON API data fetching, caching, server state management.
> **SCOPE:** TanStack Query v5, Next.js hydration, Suspense integration.

## 1. Query Patterns
- Use the `queryOptions()` factory pattern for defining query configurations (replaces raw query key factories). This ensures type-safe, reusable query definitions with co-located `queryKey` and `queryFn`.
- Separate fetcher functions from components for testability.
- Utilize Stale-While-Revalidate (SWR) logic as the default caching mechanism.
- Use `useSuspenseQuery()` (v5) for Server Component-compatible data fetching that integrates with React 19 Suspense boundaries. This eliminates manual `isLoading` handling.
- Use `useQuery()` only when Suspense integration is not desired or for non-blocking background refetches.

## 2. Mutations & Updates
- Implement Optimistic Updates for highly interactive mutations to make the UI feel instant.
- Use `onSettled` in mutations to invalidate relevant query keys and trigger refetches.
- Define retry logic appropriately (e.g., disable retries for 4xx errors, retry 5xx).

## 3. Advanced Features
- Use Infinite Queries for cursor-based or offset-based pagination.
- Prefetch queries on server or on hover (using `queryClient.prefetchQuery`) to eliminate loading spinners.
- Handle SSR effectively by dehydrating state on the server and hydrating the `QueryClientProvider` in Next.js.
- Integrate with React Error Boundaries for robust error handling.
- Use `useMutationState()` (v5) to observe mutation states across components (e.g., showing a global loading indicator for pending mutations).

## 4. Hard Constraints
- NEVER mutate the cached data directly outside of `queryClient.setQueryData`.
- NEVER use generic string arrays as query keys without the `queryOptions()` factory pattern.
- ALWAYS handle loading, error, and success states explicitly in the UI (or use `useSuspenseQuery` to eliminate loading state handling).
- NEVER use `useQuery` where `useSuspenseQuery` is more appropriate for a Suspense-driven architecture.

---

## ✅ TANSTACK QUERY COMPLIANCE CHECK (Mandatory)
- [ ] **Query Options:** Is the `queryOptions()` factory pattern used for all query definitions?
- [ ] **Mutations:** Are queries properly invalidated after successful mutations?
- [ ] **Performance:** Is prefetching or optimistic updating utilized for better UX?
- [ ] **Suspense:** Is `useSuspenseQuery()` used for Suspense-integrated data fetching?
