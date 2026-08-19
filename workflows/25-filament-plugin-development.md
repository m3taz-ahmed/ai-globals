[WORKFLOW] 25-filament-plugin-development
[OBJ] Develop custom Filament plugins implementing the Plugin interface with register/boot lifecycle.
[TRIGGER] /filament-plugin, /custom-plugin, /filament-extension, /plugin-development
[RULES]
1. [REQ] Query `tech-stack/filament-plugins` and `tech-stack/filament-{version}` before starting. Read lockfile for exact Filament version (`[VER-01]`).
2. [REQ] Create plugin class implementing `Filament\Contracts\Plugin` with `getId(): string`, `register(Panel $panel): void`, `boot(Panel $panel): void`. (Filament pattern)
3. [REQ] In `register()`: register resources, pages, widgets, clusters, livewire components. Use discovery where possible: `$panel->discoverResources(in:, for:)`. ⛔ NEVER register assets or run boot logic in `register()`.
4. [REQ] In `boot()`: add authorization gates, register render hooks, configure global component defaults via `configureUsing()`, register assets (CSS/JS via `Asset` ABC subclasses). Boot runs AFTER all plugins registered.
5. [REQ] Create config file `config/{plugin-name}.php` with env overrides. `return ['setting' => env('PLUGIN_SETTING', 'default'), ...]`. ⛔ NEVER hardcode values in plugin class.
6. [REQ] Plugin registration in PanelProvider: `->plugins([MyPlugin::make()->settingName($value)])`. Fluent configuration API via `make()` factory + setter methods.
7. [REQ] Authorization via plugin: `Plugin::make()->authorizeResource(fn() => Gate::check('edit.resource'))` per-resource authorization closures. (Filament-Blog pattern)
8. [REQ] Use `configureUsing()` for global component defaults: `Component::configureUsing(fn(Component $c) => $c->default(...))`. Important configurations applied last. (Filament ComponentManager pattern)
9. [REQ] Asset management: `Css::make('id', 'path')`, `Js::make('id', 'path')->async()->defer()`, `Theme::make('id', 'path')`. `loadedOnRequest()` for lazy assets. `package(string)` for versioning via `InstalledVersions::getVersion()`. (Filament Asset pattern)
10. [REQ] Multi-tenancy support: `->isScopedToTenant(): bool` on Resources. Config-driven: `config/{plugin}.php` `is_scoped_to_tenant => true`. Tenant model + tenant middleware. ⛔ NEVER assume single-tenant in plugin code.
11. [REQ] Navigation: `NavigationGroup::make()->label()->collapsible()` + `NavigationItem` with `is_visible` (bool|Closure), `sort`, `group`. Register via `$panel->navigationGroups([...])` + `$panel->navigationItems([...])`.
12. [REQ] Theming: `->viteTheme(string|array $theme, ?string $buildDirectory)` for custom Vite theme. `->theme(string|Htmlable|Theme)` for direct CSS. `ThemeMode::System|Light|Dark` via `defaultThemeMode()`.
13. [CMD] Query Context7 MCP for Filament plugin docs: `mcp_call_tool(context7, resolve-library-id, {libraryName: "filament/filament"})` then `get-library-docs` with full question about plugin development.
14. [CMD] Scaffold plugin: `php artisan make:class Filament/Plugins/{Name}Plugin.php` implementing `Plugin` interface.
15. [CMD] Create config: `php artisan vendor:publish --tag={plugin-name}-config` or manually create `config/{plugin-name}.php`.
16. [CMD] Register in `app/Providers/Filament/AdminPanelProvider.php`: add to `->plugins([...])`.
17. [CMD] Test plugin registration: write Pest test verifying `Panel::getPlugin('{id}')` returns instance. Use `Orchestra\Testbench` for package testing.
18. [CMD] Test multi-DB: SQLite (default) + MySQL + PostgreSQL configs. Parallel + serial groups: `--parallel --exclude-group=serial`.
19. [REQ] Plugin compatibility: pin to Filament major version. `^4.0` for Filament v4, `^5.0` for v5. ⛔ NEVER mix Filament v3 plugins with v4+ panels. Check `composer.json` constraints.
20. [REQ] Quality: run `pint`, `phpstan --level=8`, and `php artisan test --filter={PluginName}` (FAST tier) during iteration. Full suite before done. Query `laravel-testing` tech-stack.
21. [REQ] Security: query `laravel-security` tech-stack. Authorization gates on every resource. FormRequest validation. RBAC via filament-shield or custom gates. ⛔ NEVER expose plugin admin without authorization.
22. [REQ] Documentation: create `docs/{plugin-name}.md` with installation, configuration, usage examples. Update `README.md` if standalone package.
