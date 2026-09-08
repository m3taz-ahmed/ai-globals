[TECH] Livewire 4 (latest 4.4.3, Aug 2026)
[OBJ] Livewire v4.x — single-file components as default, `Route::livewire()`, `pages::`/`layouts::` namespaces, scoped `<style>`/`<script>`, `@island` for isolated re-renders, `wire:sort` drag-and-drop, `wire:transition` animations.
[RULES]
1. [REQ] Use single-file (view-based) components as default — one `.blade.php` file contains both markup + logic via `@php` blocks or companion class.
2. [REQ] Use `Route::livewire('/path', MyComponent::class)` for route registration — replaces `Route::get` + render in mount.
3. [REQ] Use `pages::` and `layouts::` namespaces for view resolution — `layouts::app` instead of `layouts.app`.
4. [REQ] Use scoped `<style>` and `<script>` tags — automatically scoped to component, no global leakage.
5. [REQ] Use `@island` for isolated re-render regions — only the island re-renders, not the full page. Reduces server load.
6. [REQ] Use `wire:sort` for drag-and-drop sorting — built-in, no Alpine plugin needed.
7. [REQ] Use `wire:transition` for smooth animations — replaces `wire:loading` spinners with transitions.
8. [REQ] `config/livewire.php` key `layout` renamed to `component_layout` — uses `layouts::` namespace.
9. [REQ] `lazy_placeholder` renamed to `component_placeholder` — update config.
10. [REQ] `wire:model` now ignores child events by default — use `.deep` modifier to restore bubbling behavior.
11. [REQ] `.blur`/`.change` modifiers now control client-side state sync too — add `.live` for old network-only behavior.
12. [REQ] Component tags must be closed — `<livewire:my-component />` or `<livewire:my-component></livewire:my-component>`.
13. [PROHIBIT] Never use `layout` config key — renamed to `component_layout`.
14. [PROHIBIT] Never use `lazy_placeholder` — renamed to `component_placeholder`.
[COMPAT]
- Livewire 4.4.3 (released Aug 31 2026).
- v4.0.0 released Jan 14 2026.
- Requires PHP 8.2+, Laravel 11.28+.
- Tailwind CSS v4+ required for Filament v5 compatibility.
- Use `vendor/bin/filament-v5` for Filament v5 upgrade (handles Livewire v4 rewrites).
[REFS]
- https://github.com/livewire/livewire/releases/tag/v4.0.0
- https://livewire.laravel.com/docs/4.x/upgrading
- https://livewire.laravel.com/docs/4.x
