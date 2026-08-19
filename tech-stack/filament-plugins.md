[TECH] filament-plugins
[OBJ] Filament Plugin Architecture & Recommended Plugins.
[RULES]
1. [REQ] Plugin Interface: Implement `Filament\Contracts\Plugin` with `getId(): string`, `register(Panel $panel): void`, `boot(Panel $panel): void`. Every feature pluggable. Register via `->plugins([Plugin::make()])` in PanelProvider.
2. [REQ] Plugin Registration: `->plugin(Plugin $plugin)` for single, `->plugins(array $plugins)` for multiple. `getPlugin(string $id): Plugin` throws `LogicException` if not registered. `hasPlugin(string $id): bool` for checks.
3. [REQ] Plugin Boot Order: `register()` called during registration (before boot). `boot()` called after ALL plugins registered. Boot callbacks run last. ⛔ NEVER assume another plugin is booted in your `register()`.
4. [REQ] Authorization via Plugin: `Plugin::make()->authorizePost(fn() => auth()->user()->can('edit.posts'))->authorizeAuthor(fn() => auth()->user()->can('edit.authors'))->authorizeCategory(fn() => auth()->user()->can('edit.category'))` (Filament-Blog pattern). Per-resource authorization closures.
5. [REQ] Recommended Plugins (production-tested from SuperDuper/MVPable):
   - `bezhansalleh/filament-shield` — RBAC + Spatie Permission integration. Auto-generate permissions. `HasShield` trait on Resources. `super_admin` bypasses all.
   - `bezhansalleh/filament-exceptions` — Exception tracking viewer. Scoped to tenant via config.
   - `jeffgreco13/filament-breezy` — Profile management + 2FA + avatar. `myProfile()` with customizable components.
   - `datlechin/filament-menu-builder` — Menu management with locations + static menu panels.
   - `tomatophp/filament-media-manager` — Media management with sub-folders.
   - `filament/spatie-laravel-media-library-plugin` — Spatie Media Library integration. Collections + conversions.
   - `filament/spatie-laravel-settings-plugin` — Spatie Settings integration. Grouped settings (general, mail, site, seo, social).
   - `filament/spatie-laravel-tags-plugin` — Spatie Tags integration. Typed tags (`->type('section_tag')`).
   - `riodwanto/filament-logger` — Activity logging. Scoped to tenant.
   - `pxlrbt/filament-activity-log` — Activity log alternative (spatie/laravel-activitylog).
   - `pxlrbt/filament-environment-indicator` — Environment indicator badge.
   - `stechstudio/filament-impersonate` — User impersonation with audit trail.
   - `opcodesio/log-viewer` — Log viewing from admin panel.
   - `flowframe/laravel-trend` — Analytics/trends for widgets.
   - `eightynine/filament-docs` — Documentation plugin in admin panel.
   - `riodwanto/filament-ace-editor` — Code editor field.
   - `jibaymcs/filament-tour` — Driver.js onboarding tours.
   - `saade/filament-laravel-log` — Read Laravel logs from admin panel.
   - `ralphjsmit/laravel-filament-seo` — SEO management for Filament.
   - `solutionforest/filament-tree` — Tree-structured model management (menus, categories).
   - `relaticle/custom-fields` — Dynamic user-defined form fields.
6. [REQ] Custom Plugin Development: Implement `Plugin` interface. Use `configureUsing()` for global component defaults. Create config file `config/{plugin-name}.php`. Register resources/pages/widgets in `register()`. Add authorization in `boot()`.
7. [REQ] Plugin Discovery: `->discoverResources(in: app_path('Filament/Resources'), for: 'App\\Filament\\Resources')` instead of manual registration. Same for Pages (`discoverPages`), Widgets (`discoverWidgets`), Clusters (`discoverClusters`). Reduces boilerplate.
8. [REQ] Plugin Configuration: `Plugin::make()->settingName($value)` fluent API. Store config in `config/{plugin-name}.php` with env overrides. ⛔ NEVER hardcode values in plugin class.
9. [REQ] Plugin Testing: Test plugin registration + boot in isolation. Use `Orchestra\Testbench` for package testing. Multi-DB (SQLite + MySQL + PostgreSQL). Parallel + serial groups.
10. [REQ] Plugin Theming: `->viteTheme(string|array $theme, ?string $buildDirectory)` for custom Vite theme. `->theme(string|Htmlable|Theme)` for direct CSS. `ThemeMode::System|Light|Dark` for mode. `defaultThemeMode()`.
11. [REQ] Plugin Assets: `Asset` ABC with `Css`/`Js`/`Theme` subclasses. `loadedOnRequest()` for lazy assets. `package(string)` for versioning. `isRemote()` for CDN detection.
12. [REQ] Plugin Navigation: `NavigationGroup::make()->label()->collapsible()` + `NavigationItem` with `is_visible` (bool|Closure), `sort`, `group`. Register via `->navigationGroups([...])` + `->navigationItems([...])`.
13. [REQ] Plugin Multi-Tenancy: `->isScopedToTenant(): bool` on Resources. Config-driven: `config/filament-shield.php` `is_scoped_to_tenant => true`. Tenant model + tenant middleware. ⛔ NEVER assume single-tenant in plugin code.
14. [REQ] Plugin Compatibility: Pin plugin versions to Filament major version. `^4.0` for Filament v4, `^5.0` for v5. ⛔ NEVER mix Filament v3 plugins with v4+ panels. Check `composer.json` constraints.
