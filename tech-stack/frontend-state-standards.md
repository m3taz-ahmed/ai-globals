# Frontend State Management Standards
> [!NOTE]
> Trigger: Building frontend interfaces, React/Vue components, deciding on data storage, or handling forms.

## 1. State Location & Scope
- **URL/Query Params:** Use URL state for filter, sort, pagination, or anything that users should be able to share or bookmark (e.g., `?category=shoes&sort=price_asc`).
- **Local Component State (`useState`):** Use for UI-only toggles (modals, dropdowns, form inputs) that don't need to be accessed globally.
- **Global State:** Only use when state must be accessed by deeply nested or unrelated components. ⛔ Do not put everything in global state.

## 2. Global State Libraries (React Ecosystem)
- **Server State (Caching/Fetching):** Use **React Query (TanStack Query)** or **SWR**. ⛔ Do not use Redux/Zustand to store raw API responses or loading flags. Let the data fetching library handle caching, retries, and invalidation.
- **Client State (UI Context):** Use **Zustand** or **React Context**.
  - Use `Context` for rarely changing state (e.g., Theme, Locale, Auth Session).
  - Use `Zustand` for frequently changing global state (e.g., Shopping Cart, Complex multi-step wizards) to prevent unnecessary re-renders.

## 3. Server-Side Rendering (SSR) State
- **Hydration:** Ensure initial client state matches server-rendered HTML to avoid hydration mismatches.
- **Security:** ⛔ Never expose sensitive database data (e.g., password hashes, internal IDs) inside the initial state payload (e.g., Next.js `getServerSideProps` or Remix loaders).

## 4. Forms & Validation
- **Form Libraries:** Use **React Hook Form** combined with **Zod** for schema validation. ⛔ Avoid uncontrolled inputs manually synced to global state on every keystroke.
- **Controlled vs Uncontrolled:** Prefer uncontrolled inputs (React Hook Form default) to avoid performance bottlenecks on large forms.

## 5. Performance Traps
- **Prop Drilling:** If you pass props down more than 3 levels, reconsider your composition (`children` prop) before resorting to Context.
- **Context Renders:** Remember that any change to a React Context value re-renders ALL consumers. Split contexts by domain if they change frequently.
