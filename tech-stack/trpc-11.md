[TECH] tRPC 11
[OBJ] End-to-end type-safe RPC framework for TypeScript with procedure-based routers, middleware, context, subscriptions, and a fully typed client.
[RULES]
1. [REQ] Define procedures using `publicProcedure`, `protectedProcedure`, or `mutation`/`query` builders; organize into routers with `t.router({ ... })` and merge sub-routers with `t.mergeRouters()`.
2. [REQ] Use Zod for input validation on every procedure: `.input(z.object({ ... }))`; validate and parse all client inputs before business logic; never trust raw client payloads.
3. [REQ] Use middleware for cross-cutting concerns (auth, logging, rate limiting); chain middleware with `.use()`; create reusable middleware with `t.middleware(async ({ ctx, next }) => { ... })`.
4. [REQ] Define context (`CreateContext`) to carry request-scoped data (user, db, headers); use `createContext` function per request; never store mutable global state in context.
5. [REQ] Use `protectedProcedure` with auth middleware for authenticated routes; throw `TRPCError` with code `UNAUTHORIZED` for missing sessions; use `TRPCError` codes (`BAD_REQUEST`, `NOT_FOUND`, `FORBIDDEN`, `INTERNAL_SERVER_ERROR`).
6. [REQ] Use the typed client (`createTRPCClient` or `createTRPCReact`) for end-to-end type inference; the client infers input/output types from server definitions automatically.
7. [REQ] Use `createTRPCReact` for React integration; use `useUtils()` (v11, formerly `useContext`) for cache manipulation; use `trpc.useQuery()` and `trpc.useMutation()` hooks.
8. [REQ] Use `httpBatchLink` for batching multiple procedure calls into a single HTTP request; configure `maxURLLength` to avoid URL length limits; use `httpLink` for non-batched transport.
9. [REQ] Use `wsLink` for subscriptions over WebSocket; implement `subscriptionProcedure` with async iterables; handle connection lifecycle and reconnection in the client.
10. [REQ] Use `superjson` as the transformer for Date/Map/Set/BigInt serialization; register it in both server `createContext` and client `httpBatchLink` configuration.
11. [REQ] Use error formatting in `errorFormatter` to customize error shape; expose `code`, `message`, and `data` (including Zod field errors) to the client; never expose stack traces.
12. [REQ] Enable response metadata via `responseMeta` for caching headers (e.g., `Cache-Control`); use `stale-while-revalidate` patterns with React Query integration.
13. [REQ] Use `t.procedure.use()` for logging and performance monitoring; integrate with OpenTelemetry for distributed tracing of procedure calls.
14. [PROHIBIT] Never expose the raw database client in context without scoping; pass a scoped/transaction-bound client to prevent cross-request data leakage.
15. [PROHIBIT] Never bypass input validation with `.input(z.any())` or `.input(z.unknown())`; every procedure must have explicit, typed input validation.
[COMPAT]
- v11.x: TypeScript 5+, Zod 3+, React 18+, Next.js 14+ (App Router), Node.js 18+
- v11.x: `@trpc/server`, `@trpc/client`, `@trpc/react-query`, `@trpc/next`, `@trpc/websocket`
- v11.x: `httpBatchLink`, `httpLink`, `wsLink`, `superjson` transformer, `unstable_httpSubscriptionLink` (SSE)
[REFS]
- https://trpc.io/docs
- https://trpc.io/docs/server/procedures
- https://trpc.io/docs/client/links
- https://trpc.io/docs/react
- https://trpc.io/docs/server/middleware
- https://trpc.io/docs/server/subscriptions
