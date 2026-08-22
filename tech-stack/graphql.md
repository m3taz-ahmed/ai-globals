[TECH] GraphQL
[OBJ] Query language and runtime for APIs with a strongly typed schema, resolver-based field resolution, subscriptions, and federation for distributed graphs.
[RULES]
1. [REQ] Define a strongly typed schema using SDL (Schema Definition Language): `type`, `input`, `interface`, `union`, `enum`, `scalar`; use `@deprecated` with migration reason for breaking field changes.
2. [REQ] Implement resolvers per field: `parent` (source), `args`, `contextValue`, `info`; keep resolvers thin — delegate to service/repository layers; avoid N+1 queries with DataLoader.
3. [REQ] Use DataLoader for batching and caching related field resolution; create per-request DataLoader instances in context to prevent cross-request cache leakage.
4. [REQ] Use mutations (`type Mutation`) for writes; accept `input` types for arguments; return the mutated entity and a `userErrors` array for partial failures; never perform writes in query resolvers.
5. [REQ] Use subscriptions (`type Subscription`) with WebSocket/SSE transport for real-time push; implement `subscribe` (async iterator) and `resolve` (transform) functions; authenticate on connection init.
6. [REQ] Implement query complexity analysis with depth limiting (max depth 5-10) and cost-based limits (e.g., `createComplexityRule({ maximumComplexity: 1000 })`); reject queries exceeding limits before execution.
7. [REQ] Implement persisted queries for production: store query hashes client-side, send hash + variables over wire; server resolves hash to stored query; reduces bandwidth and prevents injection.
8. [REQ] Use Apollo Federation (or schema stitching) for distributed schemas: define `@key`, `@extends`, `@external`, `@requires`, `@provides` directives; use `_entities` and `_service` root fields.
9. [REQ] Use `@defer` directive for streaming partial responses for slow fields; use `@stream` for list field incremental delivery; ensure transport supports multipart responses.
10. [REQ] Authenticate at the resolver or directive level using `context`; use field-level authorization with custom directives (`@auth(requires: ADMIN)`) or middleware; never rely solely on gateway auth.
11. [REQ] Use automatic persisted queries (APQ) or static persisted queries; disable introspection in production (`introspection: false`) to prevent schema leakage.
12. [REQ] Use error extensions with structured codes: `extensions: { code: 'UNAUTHENTICATED' }`; use the `formatError` function to sanitize internal errors before client exposure.
13. [REQ] Version schema changes as non-breaking first (add fields, deprecate old); use schema registry (Apollo Studio, Hive) to detect breaking changes before deployment.
14. [PROHIBIT] Never expose raw database IDs or internal identifiers in the schema; use stable business identifiers (UUIDs, slugs) to prevent coupling to storage layer.
15. [PROHIBIT] Never allow arbitrary query depth or disable complexity limits in production; malicious nested queries can cause exponential resolver calls and DoS.
[COMPAT]
- v2021 (October 2021 spec): Schema, Query, Mutation, Subscription, `@defer`, `@stream`, custom directives, introspection
- v2021: Apollo Server 4, GraphQL Yoga 5, Mercurius (Fastify), graphql-go, Strawberry (Python), Juniper (Rust)
- v2021: Apollo Federation 2, Apollo Gateway, Hive, Apollo Studio (schema registry)
[REFS]
- https://spec.graphql.org/
- https://graphql.org/learn/
- https://www.apollographql.com/docs/federation/
- https://github.com/graphql/dataloader
- https://www.apollographql.com/docs/react/data/persisted-queries/
