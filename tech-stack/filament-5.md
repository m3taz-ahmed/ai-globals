# Filament v5.x Architecture Rules
> [!NOTE]
> Status: Stable (Jan 2026). Requires Livewire v4 + PHP 8.2+.

## Livewire v4 Islands (Core)
- **Islands:** Independent renders. Widget updates must not trigger full-page re-renders. ⛔ waterfalls.
- **Filters:** Use deferred filters (`v5.2.0+`) for heavy queries to batch request execution.

## Async-First & Deferral
- **Loading:** Dashboards/tables must use `->deferLoading()` or Islands async loading for non-blocking UI.
- **Updates:** Use Laravel Reverb / SSE for real-time updates. ⛔ client-side polling.

## Component Embeds
- **Lifecycle:** Use Livewire v4 hooks (`@script`, `@assets`) for custom JS.
- **Isolation:** Scoped styles/module-pattern script. ⛔ global leaks.

## State Management
- **Enums:** Map UI states/filter actions to PHP Enums. ⛔ magic strings.
- **Size:** Component state < 50KB. Use Redis cache for larger structures.
- **Eloquent:** Pass scalar IDs only. ⛔ serialize full models in state.

## Security
- **Auth:** Implement `canViewAny`, `canCreate`, `canEdit`, `canDelete`, `canView` on resources (default deny).
- **Shield:** Enforce Panel access using `bezhansalleh/filament-shield`.
