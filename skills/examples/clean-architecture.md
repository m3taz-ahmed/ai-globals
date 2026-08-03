---
name: clean-architecture-example
---
[FILE] clean-architecture-example
[OBJ] Compressed reference card for Clean Architecture / Layered Architecture derived from ardalis/CleanArchitecture, jasontaylordev/CleanArchitecture, bxcodec/go-clean-arch, alibaba/COLA.
[CONTEXT] Use when generating service code, reviewing structure, or onboarding backend personas.
[RULES]
1. [LAYER] Dependencies point inward: Frameworks/Drivers -> Interface Adapters -> Use Cases -> Entities.
2. [LAYER] Core (Entities + Use Cases) has zero framework or UI dependencies.
3. [SERVICE] Keep controllers thin: parse input, call use case, map to DTO/response. No business rules in controllers.
4. [REPO] Repository abstraction lives in core; implementation lives in infrastructure. No raw SQL in use cases.
5. [DTO] Use explicit DTOs/records for crossing boundaries; avoid exposing ORM entities directly.
6. [TEST] Unit test use cases in isolation with in-memory repositories; integration test infrastructure; E2E test happy paths.
7. [PATTERN] Prefer CQRS only when read/write load/team ownership diverges; otherwise keep it simple.
8. [REFERENCES] `ardalis/CleanArchitecture` (ASP.NET template), `jasontaylordev/CleanArchitecture` (.NET + MediatR CQRS), `bxcodec/go-clean-arch` (Go + Echo/Gorm), `alibaba/COLA` (Java DDD + layers).
