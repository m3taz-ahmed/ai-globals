[TECH] tanstack-query
[OBJ] TanStack Query v5.
[RULES]
1. [REQ] Patterns: `queryOptions()` factory pattern (type-safe). Separate fetchers. SWR logic default.
2. [REQ] Fetching: `useSuspenseQuery()` for Server Components (React 19).
3. [REQ] Mutations: Optimistic Updates. `onSettled` to invalidate. `useMutationState()` to observe global state.
4. [PROHIBIT] Constraints: NEVER mutate cache directly (use `setQueryData`). NEVER use string arrays as query keys without factory.
