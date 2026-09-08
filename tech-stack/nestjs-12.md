[TECH] NestJS 12 (latest 12.0.0, Aug 2026)
[OBJ] Enterprise Node.js framework — ESM-first core, Standard Schema support, rebuilt CLI, `@nestjs/observe` SDK, Rspack replaces webpack, Vitest + oxlint for ESM projects.
[RULES]
1. [REQ] Use ESM-first core packages — CommonJS apps still work via `require(esm)`. New projects choose CJS or ESM at scaffold time.
2. [REQ] Use first-class Standard Schema support in decorators — validate with Zod, Valibot, or any Standard Schema-compliant library.
3. [REQ] Use rebuilt CLI — `nest new` prompts for CJS/ESM. `nest build` uses Rspack by default (replaces webpack).
4. [REQ] Use `@nestjs/observe` SDK for observability — built-in OpenTelemetry integration, tracing, metrics.
5. [REQ] Use Vitest + oxlint for ESM projects — default test runner for new ESM projects. CJS projects still use Jest.
6. [REQ] Use `@nestjs/graphql` v14 (latest 13.4.5) — `registerIn` option for module-scoped type filtering.
7. [REQ] Node.js >=20.19 or >=22.12 required — the upgrade command refuses older Node versions.
8. [REQ] Use `inject()` for dependency injection — never constructor injection in new code.
9. [REQ] Use functional guards/resolvers (`canMatch`, `canActivate`, `resolve`) with `inject()`.
10. [REQ] Use `@nestjs/microservices` for event-driven communication (TCP, Redis, NATS, RabbitMQ, Kafka).
11. [REQ] Use `@nestjs/swagger` for OpenAPI/Swagger docs generation from decorators.
12. [REQ] Use `@nestjs/typeorm` or `@nestjs/prisma` for database ORM integration.
13. [PROHIBIT] Never use `playground` (renamed to `graphiql` in GraphQL module).
14. [PROHIBIT] Never use webpack for new NestJS 12 projects — use Rspack.
15. [PROHIBIT] Never use Node.js < 20.19 — upgrade command will refuse.
[COMPAT]
- NestJS 12.0.0 (released Aug 27 2026).
- Node.js >=20.19 or >=22.12 required.
- ESM-first core (CJS via `require(esm)`).
- Rspack replaces webpack as default bundler.
- Vitest + oxlint for ESM projects, Jest for CJS.
- TypeScript 6+ required.
[REFS]
- https://github.com/nestjs/nest/releases/tag/v12.0.0
- https://docs.nestjs.com/migration-guide
- https://trilon.io/blog/nestjs-12-is-now-available
