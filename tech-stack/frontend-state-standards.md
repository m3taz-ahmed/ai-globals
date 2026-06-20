[TECH] frontend-state-standards
[OBJ] Frontend State Management Standards.
[RULES]
1. [REQ] Scope: URL for filters/sorts. `useState` for local toggles. Global ONLY when deeply nested.
2. [REQ] Server State: React Query (TanStack Query) / SWR. ⛔ DO NOT put raw API responses in Zustand/Redux.
3. [REQ] Client State: Context for rare changes (Theme/Auth). Zustand for frequent changes (Cart/Wizards).
4. [REQ] Forms: React Hook Form + Zod. Prefer uncontrolled inputs.
5. [PROHIBIT] Hydration: NEVER expose sensitive DB data in initial state payload (SSR).
