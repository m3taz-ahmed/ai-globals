[TECH] zustand-state
[OBJ] Zustand State Management.
[RULES]
1. [REQ] Architecture: "Slices Pattern" for modular stores. Keep state flat. Explicit TS interfaces.
2. [REQ] Perf: Use selectors to prevent re-renders. `useShallow` for referential equality.
3. [REQ] Next.js SSR: Handle hydration via `useStoreHydration` hook.
4. [REQ] Middleware: `persist`, `devtools`, `immer`.
5. [PROHIBIT] Constraints: NEVER store server data (use TanStack Query). NEVER mutate directly without `immer`.
