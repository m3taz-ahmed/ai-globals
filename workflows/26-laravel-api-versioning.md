[WORKFLOW] 26-laravel-api-versioning
[OBJ] Setup header-based API versioning in Laravel (Koel pattern) with versioned route files and API Resources with structure constants.
[TRIGGER] /api-versioning, /versioned-api, /api-versions, /header-versioning
[RULES]
1. [REQ] Query `tech-stack/laravel-{version}` before starting. Read `composer.lock` for exact Laravel version (`[VER-01]`). Header-based versioning requires Laravel 11+.
2. [REQ] Create `app/Providers/RouteServiceProvider.php` (or modify existing) with `loadVersionAwareRoutes(string $type): void` method. (Koel pattern)
3. [REQ] Route loading logic: load base routes from `routes/{type}.base.php`, then read `X-Api-Version` header via `request()->header('X-Api-Version')`, load versioned routes from `routes/{type}.{version}.php` if file exists.
4. [REQ] Base routes in `routes/api.base.php` — endpoints available in ALL versions. Versioned routes in `routes/api.{version}.php` — endpoints specific to that version. ⛔ NEVER version in URL path (`/v1/...`) for new APIs; prefer header-based.
5. [REQ] Register `loadVersionAwareRoutes('api')` in `boot()` method of `RouteServiceProvider`. Call within `Route::middleware(['api'])` group.
6. [REQ] API Resources with structure constants: `class SongResource extends JsonResource { public const array JSON_STRUCTURE = ['type','id','title',...]; public const array PAGINATION_JSON_STRUCTURE = ['data' => [0 => self::JSON_STRUCTURE], 'links' => [...], 'meta' => [...]]; public const array CURSOR_PAGINATION_JSON_STRUCTURE = [...]; }`. (Koel pattern)
7. [REQ] Test structure: `->assertJsonStructure(Resource::JSON_STRUCTURE)` + `->assertJsonStructure(Resource::PAGINATION_JSON_STRUCTURE)` for every API endpoint. Structure constants on `JsonResource` classes.
8. [REQ] Cursor pagination for large datasets (>10k rows): `->cursorPaginate()`. `PaginationStrategy` resolver selects cursor vs offset based on request. Test cursor traversal across all sort columns without duplicates.
9. [REQ] Versioned controllers: `app/Http/Controllers/Api/V{N}/{Controller}.php` for version-specific logic. OR use `Accept: application/vnd.api+json;version=N` content negotiation as alternative.
10. [REQ] Deprecation headers: add `Sunset` HTTP header for endpoints being removed in next version. `Deprecation` header for deprecated but functional endpoints. Document sunset date in OpenAPI spec.
11. [REQ] OpenAPI/Scribe documentation: generate per-version docs. `@group` and `@response` annotations with version tags. Versioned API explorer UI.
12. [CMD] Query Context7 MCP for Laravel routing docs: `mcp_call_tool(context7, resolve-library-id, {libraryName: "laravel/framework"})` then `get-library-docs` with full question about API versioning and route loading.
13. [CMD] Create base route file: `php artisan make:command` not needed — manually create `routes/api.base.php` with base endpoints.
14. [CMD] Create versioned route file: manually create `routes/api.{version}.php` (e.g. `routes/api.1.php`).
15. [CMD] Create/modify `RouteServiceProvider.php` with `loadVersionAwareRoutes()` method.
16. [CMD] Create API Resources: `php artisan make:resource Api/{Model}Resource` with `JSON_STRUCTURE` constants.
17. [CMD] Create FormRequests with `toDto()`: `php artisan make:request Api/{Model}Request` with `rules()` + `toDto(): SomeData`.
18. [CMD] Create DTOs in `app/Values/`: `php artisan make:class Values/{Name}Data` with named-argument constructor.
19. [CMD] Test version routing: write Pest test sending `X-Api-Version: 1` header and verifying correct controller/route is hit. Test base routes work without version header.
20. [CMD] Test structure constants: `->assertJsonStructure(Resource::JSON_STRUCTURE)` in every API test.
21. [CMD] Test cursor pagination: traverse all sort columns without duplicates (Koel pattern).
22. [REQ] Quality: run `pint`, `phpstan --level=8`, and `php artisan test --filter=Api` (FAST tier) during iteration. Full suite before done. Query `laravel-testing` tech-stack.
23. [REQ] Security: query `laravel-security` tech-stack. `throttle:api` on all API endpoints. Sanctum auth. FormRequest validation. RBAC policies. ⛔ NEVER expose API without auth + rate limiting.
24. [REQ] Backward compatibility: maintain base routes across all versions. Breaking changes ONLY in new version files. Document migration guide for each version bump.
