[TECH] filament-4
[OBJ] Filament v4.x Architecture Rules.
[RULES]
1. [REQ] Design: Group via Clusters. `InfoLists` for read-only data. Custom logic in Actions.
2. [REQ] Optimization: Fluent chaining only (PHPStan Lvl 8). `eagerLoad()` on ALL tables. Polling >30s.
3. [REQ] Structure: Use PHP 8.4 property hooks. Use Filament native multi-tenancy.
4. [REQ] Custom Namespaces: Use `Filament\Schemas\Components` (NOT `Filament\Forms\...`). Use `configure()` from Schema classes.
5. [REQ] Tab-based Forms: `Tabs::make()` with logical tabs (Content/SEO/Settings/Media). ⛔ NEVER one long form. Split into tabs by domain concern.
6. [REQ] Status Enum System: `enum Status implements HasColor, HasIcon, HasLabel` with backed string values. 7 states: Publish, Future, Draft, Auto, Pending, Private, Trash. ⛔ NEVER string status column. Use backed enum with colors/icons.
7. [REQ] Upload/URL Toggle: `ToggleButtons::make('media_type')->options(['upload','url'])->live()` + `visible(fn(Get $get) => $get('media_type') === 'upload')` for flexible media input.
8. [REQ] Configurable Content Editor: `HasContentEditor` trait + `config('package.editor')` for pluggable editors (RichEditor / MarkdownEditor / TinyEditor). Toolbar buttons from config.
9. [REQ] Create Option Forms: `Select::make('category_id')->relationship()->createOptionForm([...])->preload()->searchable()` for inline creation without leaving page.
10. [REQ] Navigation Badges: `getNavigationBadge(): ?string` to show record counts in sidebar. Respect visibility config.
11. [REQ] Custom Permission Prefixes: `getPermissionPrefixes(): array` with granular actions (view, view_any, create, update, delete, publish, archive, feature, approve, schedule, manage_seo, view_analytics).
12. [REQ] Role-based Field Visibility: `->disabled(fn(?Model $record) => auth()->user()?->hasRole('author'))` for role-aware form fields.
13. [REQ] Dynamic Branding from Settings: `->brandName(fn(GeneralSettings $s) => $s->brand_name)` + `->colors(fn(GeneralSettings $s) => $s->site_theme)`. Use Spatie Laravel Settings for config-driven branding.
14. [REQ] Discovery Pattern: `->discoverResources(in: app_path('Filament/Resources'), for: 'App\\Filament\\Resources')` instead of manual registration. Same for Pages, Widgets, Clusters.
15. [REQ] Authorization via Plugin: `Plugin::make()->authorizeResource(fn() => Gate::check('edit.resource'))` for per-plugin authorization gates.
16. [REQ] Action Groups: `ActionGroup::make([EditAction, Action::preview->openUrlInNewTab(), DeleteAction])` for consistent record actions.
17. [REQ] Search Highlighting: `highlightSearchResults(Collection, ?string $search)` trait for frontend search with visual feedback.
