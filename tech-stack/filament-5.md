[TECH] filament-5
[OBJ] Filament v5.x Architecture Rules.
[RULES]
1. [REQ] Islands: Livewire v4 independent renders. â›” waterfalls. Deferred filters for heavy queries.
2. [REQ] Async/Defer: `->deferLoading()`. Reverb/SSE for real-time. â›” client-side polling.
3. [REQ] Components: Scoped styles. v4 hooks (`@script`, `@assets`).
4. [REQ] State: PHP Enums for UI state. State < 50KB (Redis otherwise). Pass scalar IDs (â›” full models).
5. [REQ] Static Props (Fatal Error Fix): Match exact union types when overriding static properties (e.g. `protected static string|BackedEnum|null $navigationIcon`). NO `?string`.
6. [REQ] JS-Only Actions in Notifications: When creating an Action inside a Notification that only executes JS (e.g. `window.navigator.clipboard`), do NOT embed HTML directly in the body (stripped by XSS sanitizer), and do NOT use `->url('#')` (triggers Livewire hashchange which clears password fields). Instead, use `->alpineClickHandler("JS_CODE_HERE")` on the `Action` object to ensure the JS is executed without mounting the action in Livewire (avoiding `MethodNotFoundException: mountAction` after serialization).
7. [REQ] `HasAvatar` + Strict Eloquent: In `getFilamentAvatarUrl()`, never access optional columns via `$this->avatar` when `Model::shouldBeStrict()` / `preventsAccessingMissingAttributes()` is active, or an un-reloaded model will throw `MissingAttributeException`. Use `data_get($this->getAttributes(), 'avatar')` (or a null-safe accessor) and pass the value to the URL helper.
8. [REQ] Livewire CSP-safe build: Filament v5 UI (e.g. `fi-theme-switcher`) uses Alpine `x-init` with arrow functions. The CSP-safe Alpine build (`LIVEWIRE_CSP_SAFE=true`) cannot parse these expressions and throws `CSP Parser Error: Unexpected token: PUNCTUATION ")"`, causing the page to mount nothing (blank). For local Filament development, set `LIVEWIRE_CSP_SAFE=false` in `.env`. Only enable `true` in production with a strict nonce-based CSP and verified CSP-compatible expressions.
9. [REQ] Schema Pattern: Use `Filament\Schemas\Components` (NOT `Filament\Forms\...` or `Filament\Infolists\...`). Schema is the unified component composition system in v5. `configure()` from Schema classes. `Schema::make()->components([...])` for both forms and infolists.
10. [REQ] Plugin System: `Plugin` interface with `getId(): string`, `register(Panel): void`, `boot(Panel): void`. Every feature pluggable. Register via `->plugins([Plugin::make()])` in PanelProvider. Use `configureUsing()` for global component defaults.
11. [REQ] Cluster Pattern: `Cluster` base class for organizing related pages. `protected static ?string $navigationIcon`, `$navigationLabel`. Sub-pages extend Cluster. Register via `->discoverClusters(in:, for:)`.
12. [REQ] ComponentManager: Centralized configuration via `ComponentManager::resolve()->configureUsing(static::class, $callback)`. Class hierarchy cache + setup method cache. Important configurations applied last. `Configurable` trait on all components.
13. [REQ] EvaluatesClosures: Automatic dependency injection for closures. `evaluate($value, namedInjections, typedInjections)` resolves closure params by name, type, default, or evaluation identifier. Enables `fn(Get $get, Set $set, Model $record) => ...` without manual DI.
14. [REQ] Macroable: Runtime method extension via `static::macro(name, callable)` + `mixin(object)`. Per-class macro registry with parent fallback. Use for package-level extensions without inheritance.
15. [REQ] Registry Pattern: `PanelRegistry` with `register(Panel)`, `getDefault()`, `get(?id, isStrict)`. Strict + normalized (case-insensitive, hyphen-underscore agnostic) lookups.
16. [REQ] NavigationManager: Groups + hierarchy + sorting. `NavigationGroup::make()->label()->collapsible()`. `NavigationItem` with `is_visible` (bool|Closure), `sort`, `group`. Mount-on-demand with caching.
17. [REQ] Asset Management: `Asset` ABC with `Css`/`Js`/`Theme` subclasses. Versioned via `InstalledVersions::getVersion()`. `loadedOnRequest()` for lazy assets. `isRemote()` detection. Vite integration via `viteTheme()`.
18. [REQ] Multi-DB Testing: SQLite (default) + MySQL + PostgreSQL configs (`phpunit.{driver}.xml`). Parallel + serial groups: `--parallel --exclude-group=serial` + `--group=serial`. Browser testing via `pestphp/pest-plugin-browser`.
19. [REQ] Spatie Media Library Integration: `InteractsWithMedia` + collections per content type. `SpatieMediaLibraryFileUpload` with disk from plugin config. â›” NEVER plain `FileUpload` for complex media. Use collections + conversions.
20. [REQ] Spatie Tags with Types: `SpatieTagsInput::make('tags')->type('section_tag')` for typed taxonomy. Differentiate tags vs categories via `type` parameter.

21. [REQ] Page-Based Custom UI: Extend Filament\Pages\Page (not Resource) for non-CRUD interfaces (kanban boards, dashboards, calendars). Register via plugin or panel ->pages().
22. [REQ] Enum Trait Pattern: IsKanbanStatus trait adding statuses() method to enums for domain-specific behavior (board columns, status transitions). Use for any enum-driven UI component.
23. [REQ] Minimal Plugin Pattern: Plugin with empty egister()/oot() as marker only, functionality in Page classes. Use when feature is page-centric, not resource-centric.
24. [REQ] View Customization Hooks: Override $view, $headerView, $recordView, $statusView per page for granular Blade template customization. Use for white-label or per-tenant UI variations.
25. [REQ] Asset Publishing via Install Command: hasInstallCommand() with publishAssets() for CSS/JS delivery. FilamentAsset::register() with loadedOnRequest() for lazy-loaded JS. AlpineComponent + Js + Css asset types.
