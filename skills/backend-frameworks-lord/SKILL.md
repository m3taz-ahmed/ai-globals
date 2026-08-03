---
name: backend-frameworks-lord
description: Architect-level command of Laravel, Filament, Nova, Django, Spring Boot, Express, NestJS, Rails, ASP.NET Core.
---
[SKILL] backend-frameworks-lord
[OBJ] Design server-side apps and admin panels across Laravel, Filament, Nova, Django, Spring Boot, Express, NestJS, Rails, ASP.NET Core.
[RULES]
1. [CMD] IDs: Laravel `/laravel/docs`, Django `/websites/djangoproject_en_5_2`, Spring Boot `/spring-projects/spring-boot`, Express `/expressjs/express`, NestJS `/websites/nestjs`, Rails `/websites/guides_rubyonrails_v8_0`, ASP.NET Core `/dotnet/aspnetcore.docs`; Filament `/filamentphp/filament`; Filament Shield `/bezhansalleh/filament-shield`; Laravel Nova `/websites/nova_laravel_v5`; Laravel multi-tenancy `/spatie/laravel-multitenancy`, `/archtechx/tenancy`; Prisma `/prisma/web` source `/prisma/prisma`; MariaDB `mariadb-lord`; page sections `page-sections-lord`.
2. [REQ] Pillar coverage: request lifecycle, DI/IoC, data access/ORM, validation/serialization, auth/authz, API design, async/background work, testing, performance/operations.
3. [REQ] Query framework ID with full question + topic (routing, orm, validation, authentication).
4. [REQ] Framework choice: compare language ecosystem, concurrency model, ORM, deployment target, team skills.
5. [REQ] Laravel + MariaDB + multi-tenancy: query `backend-frameworks-lord`, `mariadb-lord`, and the chosen tenancy package; choose database-per-tenant vs schema-per-tenant vs table-per-tenant based on isolation, scale, and ops cost.
6. [REQ] Filament/Nova + MariaDB + multi-tenancy: use `mariadb-lord` for engine/security; Filament tenancy via panel tenant model + `filament-shield` RBAC; Nova tenancy via global scopes or tenant-aware policies.
7. [REQ] Landing/page builder in Laravel: query `page-sections-lord` for the standard Page + StaticPage + Filament Builder pattern; query `frontend-frameworks-lord` for section component rendering.
8. [REQ] Cite version-specific APIs when named; otherwise prefer latest stable major.
