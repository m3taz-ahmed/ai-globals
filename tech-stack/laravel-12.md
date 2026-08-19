[TECH] laravel-12
[OBJ] Laravel 12.x Architectural Standards.
[RULES]
1. [REQ] Types: Native type-hints (NO `resolve()`). Native return types for Controllers/Services/Jobs.
2. [REQ] Validation: Dedicated `FormRequest` for POST/PUT. Use custom `Rule` objects over complex regex.
3. [REQ] Async: Queue operations >100ms. Use `Bus::batch()`. Cache expensive results.
4. [REQ] Repository Pattern: Base `Repository` class with `model(): string` returning Contract interface (NOT Model class directly). Use `prettus/l5-repository` for caching + criteria, or custom base with `auth(): Authenticatable` helper. ⛔ NEVER access Model directly from Controller. Use Repository or Service.
5. [REQ] Service Layer: `BaseService` with `rules(): array` + `permissions(): array` + `execute(array $data)`. Permission dependencies system: each permission requires simpler permissions (e.g. `author_must_be_vault_manager` requires `vault_must_belong_to_account`). `QueuableService` for async operations (`ShouldQueue` + `handle()` + `$tries = 1`).
6. [REQ] DTO/Value Objects: `app/Values/` folder for complex data transfer. FormRequest with `toDto(): SomeData` method to convert validated input to DTO. Named arguments in DTO constructors. ⛔ NEVER pass raw `array $data` between Service layers. Use DTO.
7. [REQ] Three-Component Model (enterprise): Contract (Interface) + Model (Eloquent) + Proxy (Facade-like) for decoupling. `model(): string` in Repository returns Contract, not Model. Eases testing and mocking.
8. [REQ] Activity Logging: `ActivityLogger` pattern for all create/update/delete operations. `ActivityService::add(ActivityType::X, $entity)`. Activity assertions in tests: `assertActivityExists(ActivityType::COMMENT_CREATE)`.
9. [REQ] UUID Primary Keys: `use HasUuids` for distributed systems. ⛔ NEVER expose sequential IDs in API responses.
10. [REQ] Domain-Driven Structure (advanced/enterprise): `app/Domains/{Domain}/{UseCase}/` separation by business capability, NOT technical layer. `app/Actions/{Domain}/{ActionName}.php` for single-use operations. `app/Support/{HelperName}.php` for stateless helpers.
