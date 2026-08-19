[WORKFLOW] 24-laravel-architecture-setup
[OBJ] Scaffold Laravel architecture patterns (Service Layer / Repository / DTO / Actions / DDD) based on project complexity.
[TRIGGER] /laravel-architecture, /service-layer, /repository-pattern, /ddd-setup, /domain-driven
[RULES]
1. [REQ] Detect project complexity from spec: Simple (CRUD app) / Medium (business logic) / Advanced (API-first) / Enterprise (multi-domain). Query `skills/backend-frameworks-lord` Pattern Selection Matrix.
2. [REQ] For Medium+: create `app/Services/BaseService.php` with `rules(): array`, `permissions(): array`, `execute(array $data)`, `validateRules(array $data): bool`. Permission dependencies system: `private static array $permissionDependencies = ['author_must_be_vault_manager' => ['vault_must_belong_to_account', 'author_must_belong_to_account'], ...]`. (Monica pattern)
3. [REQ] For Medium+: create `app/Repositories/Repository.php` base class with `model(): string` returning Contract interface (NOT Model directly). Use `prettus/l5-repository` for caching + criteria, OR custom base with `auth(): Authenticatable` helper. Create per-domain repositories: `app/Repositories/{Domain}Repository.php`. (Bagisto/Krayin/Koel pattern)
4. [REQ] For Medium+: create `app/Http/Resources/{Model}Resource.php` extending `JsonResource` with `JSON_STRUCTURE` + `PAGINATION_JSON_STRUCTURE` constants. `->assertJsonStructure(Resource::JSON_STRUCTURE)` in tests. (Koel pattern)
5. [REQ] For Advanced: create `app/Values/` folder for DTOs. FormRequest with `toDto(): SomeData` method. Named arguments in DTO constructors: `SomeData::make(title:, artistName:, ...)`. ⛔ NEVER pass raw `array $data` between Service layers. (Koel pattern)
6. [REQ] For Advanced: create `app/Builders/` folder for custom Eloquent builders. `#[UseEloquentBuilder]` attribute on Models. Encapsulate complex scopes in Builder class with typed scope methods. (Koel pattern)
7. [REQ] For Advanced: create `app/Casts/` folder for custom casts. Implement `CastsAttributes` with typed `get()`/`set()`. Use for lyrics, preferences, storage types, JSON-encoded domain objects. (Koel pattern)
8. [REQ] For Advanced: create `app/Contracts/` or `app/Interfaces/` for swappable implementations. Bind in service provider. Enables fakes in tests (`FakePlusLicenseService`, `FakeNetwork`). (Koel pattern)
9. [REQ] For Enterprise: create `app/Domains/{Domain}/{UseCase}/` structure. Each UseCase has `Services/`, `Web/Controllers/`, `Web/ViewHelpers/`, `Api/` subfolders. Separate by business capability, NOT technical layer. (Monica pattern)
10. [REQ] For Enterprise: create `app/Actions/{Domain}/{ActionName}.php` as invokable single-use classes. `class CheckoutPlan { public function __invoke(User $user, Plan $plan): Checkout { ... } }`. (MVPable pattern)
11. [REQ] For Enterprise: create `app/Support/{HelperName}.php` for stateless helpers. `Support/Branding.php`, `Support/Seo.php`. Static methods only. (MVPable pattern)
12. [REQ] For Enterprise (modular): use `konekt/concord` for module system. `config/concord.php` with `'modules' => [ModuleServiceProvider::class, ...]`. Each module in `packages/{Vendor}/{Module}/src/` with `Contracts/`, `Models/`, `Repositories/`, `Http/`, `Providers/ModuleServiceProvider.php`. (Bagisto/Krayin pattern)
13. [REQ] For Enterprise: Three-Component Model — Contract (Interface) + Model (Eloquent) + Proxy (Facade-like). `model(): string` in Repository returns Contract. Eases testing + mocking + decoupling. (Bagisto pattern)
14. [REQ] Activity Logging (all levels): `app/Activity/Tools/ActivityLogger.php`. `ActivityService::add(ActivityType::X, $entity)` for all create/update/delete. Activity assertions in tests: `assertActivityExists(ActivityType::COMMENT_CREATE)`. (BookStack pattern)
15. [REQ] UUID Primary Keys (Advanced+): `use HasUuids` on Models. ⛔ NEVER expose sequential IDs in API responses. (Monica/Koel pattern)
16. [CMD] Query Context7 MCP for Laravel latest patterns before implementation: `mcp_call_tool(context7, resolve-library-id, {libraryName: "laravel/framework"})` then `get-library-docs`.
17. [CMD] Run `composer require prettus/l5-repository` (if using Prettus) or skip for custom base.
18. [CMD] Create base classes: `php artisan make:class Services/BaseService`, `php artisan make:class Repositories/Repository`, etc.
19. [CMD] Create one example Service + Repository + Resource + DTO per domain to establish pattern.
20. [CMD] Run `php artisan test --filter=<new feature>` (FAST tier) during iteration.
21. [REQ] Quality: run `pint`, `phpstan --level=8`, and full `php artisan test` (FULL tier) before done. Query `laravel-testing` tech-stack for two-tier testing rules.
22. [REQ] Security: query `laravel-security` tech-stack. FormRequest validation for every POST/PUT. RBAC policies + gates. `$fillable` whitelist on every Model. ⛔ NEVER `$guarded = []`.
