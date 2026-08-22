[TECH] laravel-12
[OBJ] Laravel 12.x Architectural Standards.
[RULES]
1. [REQ] Types: Native type-hints (NO `resolve()`). Native return types for Controllers/Services/Jobs.
2. [REQ] Validation: Dedicated `FormRequest` for POST/PUT. Use custom `Rule` objects over complex regex.
3. [REQ] Async: Queue operations >100ms. Use `Bus::batch()`. Cache expensive results.
4. [REQ] Repository Pattern: Base `Repository` class with `model(): string` returning Contract interface (NOT Model class directly). Use `prettus/l5-repository` for caching + criteria, or custom base with `auth(): Authenticatable` helper. â›” NEVER access Model directly from Controller. Use Repository or Service.
5. [REQ] Service Layer: `BaseService` with `rules(): array` + `permissions(): array` + `execute(array $data)`. Permission dependencies system: each permission requires simpler permissions (e.g. `author_must_be_vault_manager` requires `vault_must_belong_to_account`). `QueuableService` for async operations (`ShouldQueue` + `handle()` + `$tries = 1`).
6. [REQ] DTO/Value Objects: `app/Values/` folder for complex data transfer. FormRequest with `toDto(): SomeData` method to convert validated input to DTO. Named arguments in DTO constructors. â›” NEVER pass raw `array $data` between Service layers. Use DTO.
7. [REQ] Three-Component Model (enterprise): Contract (Interface) + Model (Eloquent) + Proxy (Facade-like) for decoupling. `model(): string` in Repository returns Contract, not Model. Eases testing and mocking.
8. [REQ] Activity Logging: `ActivityLogger` pattern for all create/update/delete operations. `ActivityService::add(ActivityType::X, $entity)`. Activity assertions in tests: `assertActivityExists(ActivityType::COMMENT_CREATE)`.
9. [REQ] UUID Primary Keys: `use HasUuids` for distributed systems. â›” NEVER expose sequential IDs in API responses.
10. [REQ] Domain-Driven Structure (advanced/enterprise): `app/Domains/{Domain}/{UseCase}/` separation by business capability, NOT technical layer. `app/Actions/{Domain}/{ActionName}.php` for single-use operations. `app/Support/{HelperName}.php` for stateless helpers.

11. [REQ] Command Object Pattern: Decompose complex service methods into discrete command classes (
ew MarkPaid(), 
ew ApplyNumber()). Each command has execute() + optional ollback(). CommandBus runs sequence with Saga-style rollback on failure. Better testability + single responsibility than monolithic services.
12. [REQ] Custom Casts to DTOs: Cast Eloquent columns to DTOs (InvoiceBackup::class, InvoiceSync::class) in model $casts. Encapsulates serialization logic, keeps models clean. Use for JSON columns with complex structure.
13. [REQ] Fluent Service Chaining: Service methods return $this for chaining (markPaid()->save()->sendEmail()). Combined with Command objects for complex workflows.
14. [REQ] Package-Based Modularity (enterprise): 41 self-contained packages in packages/Webkul/ with per-package PSR-4 autoload + per-package test suites. Each package independently testable. Use for large apps (>50 models).
15. [REQ] Search Engine Abstraction: setSearchEngine() in Repository to switch between database and Elasticsearch. Search engine interface with DB + ES implementations. Allows swapping search backends without changing business logic.
