[TECH] laravel-13
[OBJ] Laravel 13.x Strict Standards (Stable Mar 2026).
[RULES]
1. [REQ] Types: PHP 8.4 asymmetric visibility (`public private(set)`). Native Attributes. `strict_types=1`.
2. [REQ] Context API: Inject trace/tenant IDs into `Context`. Auto-propagate to logs/queues.
3. [REQ] Engine: Bind infra in `bootstrap/app.php`. ⛔ dead service providers.
4. [REQ] AI/Features: Use native `whereVectorSimilarTo()`. Stream LLM via `->stream()`. JSON:API native structures.
5. [OPS] Environment file precedence: Laravel's `LoadEnvironmentVariables` auto-selects `.env.{APP_ENV}` when `APP_ENV` is set and that file exists. Do NOT commit `.env.staging`/`.env.production` to the repo; use `.env.staging.example` templates and add `.env.*` to `.gitignore`.
6. [REQ] Custom Eloquent Builders: `app/Builders/` folder with `#[UseEloquentBuilder]` attribute on Models. Encapsulate complex scopes in Builder class instead of Model. `SongBuilder`/`AlbumBuilder` pattern with typed scope methods.
7. [REQ] Custom Casts: `app/Casts/` folder for complex data transformations. Implement `CastsAttributes` with typed `get()`/`set()`. Use for lyrics, preferences, storage types, JSON-encoded domain objects.
8. [REQ] API Resources + Structure Constants: `JsonResource` with `JSON_STRUCTURE` + `PAGINATION_JSON_STRUCTURE` + `CURSOR_PAGINATION_JSON_STRUCTURE` constants. Test against structure: `->assertJsonStructure(Resource::JSON_STRUCTURE)`. ⛔ NEVER inline response shapes in controllers.
9. [REQ] API Versioning (header-based): `X-Api-Version` header → `routes/api.{version}.php`. `RouteServiceProvider::loadVersionAwareRoutes(string $type)` loads base + versioned route files. Base routes in `routes/api.base.php`. ⛔ NEVER version in URL path (`/v1/...`) for new APIs; prefer header-based.
10. [REQ] Cursor Pagination: For large datasets (>10k rows), use cursor pagination (`->cursorPaginate()`). `PaginationStrategy` resolver selects cursor vs offset based on request. Test cursor traversal across all sort columns without duplicates.
11. [REQ] Contracts/Interfaces: `app/Contracts/` or `app/Interfaces/` for swappable implementations. `Encyclopedia`, `ObjectStorageInterface`, `PaginationStrategy`. Bind in service provider. Enables fakes in tests (`FakePlusLicenseService`, `FakeNetwork`).
12. [REQ] License/Feature Gating: `RestrictPlusFeatures` middleware for feature flags. `HandleDemoMode` for demo environments. `ForceHttps` for production. Register in `bootstrap/app.php` via `$middleware->api(append: [...])`.
