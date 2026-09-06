[TECH] NestJS 12.0
[OBJ] Enterprise Node.js framework — ESM-ready packages, Standard Schema validation, rebuilt CLI, `@nestjs/observe`, `nest upgrade`/`nest deploy`.
[RULES]
1. [REQ] Node v20.19+ or v22.12+ required — older Node versions fail at install. Verify with `node -v` before scaffolding.
2. [REQ] Packages are ESM-ready; CommonJS still works via `require(esm)` shim. Prefer ESM `"type": "module"` for new projects.
3. [REQ] Use first-class Standard Schema validation (Zod v4 / Valibot / ArkType) in DTOs and pipes — replace `class-validator` + `class-transformer` for new code.
4. [REQ] Use `@nestjs/observe` for reactive observables / telemetry instead of manual RxJS wiring in providers.
5. [REQ] Use rebuilt CLI: `nest new`, `nest generate`, `nest build`, `nest upgrade` (bump deps + run migrations), `nest deploy` (platform-agnostic deploy).
6. [REQ] Run `nest upgrade` after pulling latest framework patches — it handles breaking dep bumps automatically.
7. [REQ] Use `nest deploy` for CI/CD deploy steps instead of platform-specific scripts.
8. [REQ] GraphQL: GraphiQL replaces Apollo Playground as default IDE — update CORS / endpoint config accordingly.
9. [REQ] Config validation: Joi bumped — review `ConfigModule.forRoot({ validationSchema })` for new Joi API.
10. [REQ] NATS package replaced — migrate `@nestjs/microservices` NATS transport imports to the new package; update connection options.
11. [REQ] Jest bumped — update test configs (`jest.config.ts`), snapshot formats may differ; run `nest upgrade` to align.
12. [REQ] Use modular architecture: controllers thin, services + repositories, dependency injection via `@Injectable()`.
13. [REQ] Use guards (`@UseGuards`) + interceptors + pipes for cross-cutting concerns; never inline auth/validation in controllers.
14. [REQ] Use `@Module()` with providers/imports/exports; keep modules feature-scoped.
15. [PROHIBIT] Never use `class-validator`/`class-transformer` for new DTOs — use Standard Schema validators.
16. [PROHIBIT] Never assume Apollo Playground is available — GraphiQL is the default GraphQL IDE.
17. [PROHIBIT] Never run on Node < v20.19 — install will fail or runtime will crash.
18. [CMD] `nest new my-app` — scaffold new project.
19. [CMD] `nest upgrade` — upgrade framework + deps + run migrations.
20. [CMD] `nest deploy` — deploy to configured platform.
[COMPAT]
- Node v20.19+ / v22.12+ required.
- ESM packages; CommonJS via `require(esm)`.
- Standard Schema: Zod v4, Valibot, ArkType supported natively.
- GraphQL: GraphiQL default (Playground removed).
- NATS transport: new replacement package.
- Jest bumped (snapshot format changes).
- Joi bumped (config validation API changes).
[REFS]
- https://nestjs.com/
- https://docs.nestjs.com/
- https://docs.nestjs.com/cli/overview
