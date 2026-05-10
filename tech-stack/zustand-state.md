# Tech-Stack: Zustand State

> [!NOTE]
> **TRIGGER:** LOAD ON frontend state management, global store creation.
> **SCOPE:** Zustand, React, Next.js App Router.

## 1. Store Architecture
- Implement the "Slices Pattern" for modularizing large stores (e.g., `createBoundStore` combining `userSlice` and `uiSlice`).
- Keep state as flat as possible.
- Use explicit TypeScript interfaces for store state and actions.

## 2. Usage Patterns & Performance
- Use selectors to prevent unnecessary re-renders (e.g., `const user = useStore((state) => state.user)`).
- Use `useShallow` for selecting multiple properties when referential equality is needed.
- Handle SSR hydration properly in Next.js by using a custom hook (`useStoreHydration`) or ensuring stores are initialized client-side to prevent hydration mismatches.

## 3. Middleware
- Use `persist` middleware for storing user preferences in `localStorage`.
- Use `devtools` middleware for debugging state in development.
- Use `immer` middleware for updating deeply nested state easily.

## 4. Hard Constraints
- NEVER store server data in Zustand; use TanStack Query for remote data fetching and caching.
- NEVER mutate state directly unless using the `immer` middleware.
- ALWAYS type store actions and state comprehensively.

---

## ✅ ZUSTAND STATE COMPLIANCE CHECK (Mandatory)
- [ ] **Separation of Concerns:** Is the store only managing client state, leaving server state to TanStack Query?
- [ ] **Performance:** Are selectors used to extract specific state pieces and avoid re-renders?
- [ ] **SSR:** Is hydration handled properly to prevent Next.js mismatch errors?
