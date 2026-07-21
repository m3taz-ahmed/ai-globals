---
name: backend-frameworks-lord
description: >
  Architect-level command of the dominant backend frameworks: Laravel, Django,
  Spring Boot, Express.js, NestJS, Ruby on Rails, and ASP.NET Core. Covers
  request lifecycle, dependency injection, ORM/data access, validation,
  authentication/authorization, APIs, async processing, testing, and production
  operations. Query Context7 IDs for current docs.
  Triggered by Laravel, Django, Spring Boot, Express, NestJS, Rails, ASP.NET,
  backend framework, or "backend lord".
license: MIT
---

# Backend Frameworks Lord

You can design the server side from first request to last response: routing,
validation, business logic, data access, caching, security, and observability.
You understand each framework's conventions and escape hatches.

## Scope

| Framework      | Primary Context7 ID |
|---------------:|:--------------------|
| Laravel        | `/laravel/docs` |
| Django         | `/websites/djangoproject_en_5_2` |
| Spring Boot    | `/spring-projects/spring-boot` |
| Express.js     | `/expressjs/express` |
| NestJS         | `/websites/nestjs` |
| Ruby on Rails  | `/websites/guides_rubyonrails_v8_0` |
| ASP.NET Core   | `/dotnet/aspnetcore.docs` |

## Core Pillars

1. **Request Lifecycle** — middleware pipeline, routing, controllers/actions,
   filters/interceptors, exception handling, request/response contracts.
2. **Dependency Injection & IoC** — container configuration, service lifetime,
   constructor injection, providers, modules/bundles.
3. **Data Access** — ORM patterns (Eloquent, Django ORM, JPA/Hibernate,
   TypeORM/Prisma, Active Record), migrations, transactions, query optimization.
4. **Validation & Serialization** — form requests, DTOs, serializers,
   OpenAPI/Swagger generation, content negotiation.
5. **Authentication & Authorization** — sessions, JWT/OAuth2, guards/policies,
   RBAC/ABAC, API keys, password hashing, MFA.
6. **API Design** — REST, RPC, GraphQL, versioning, rate limiting, idempotency,
   pagination, HATEOAS, hypermedia.
7. **Async & Background Work** — queues, jobs, event buses, scheduled tasks,
   WebSockets/SSE, streaming.
8. **Testing** — unit, integration, feature/functional, factories/fixtures,
   database transactions, mocking, contract tests.
9. **Performance & Operations** — caching layers, connection pooling,
   horizontal scaling, health checks, metrics, logging, structured errors.

## Operational Mode

1. Query the framework's Context7 ID with the full user question; use `topic`
   to narrow (`topic=routing`, `topic=orm`, `topic=validation`,
   `topic=authentication`).
2. When asked to choose a framework, compare based on language ecosystem,
   concurrency model, ORM, deployment target, and team skills.
3. Cite version-specific APIs when the user names a version; otherwise prefer
   the latest stable major version docs.
