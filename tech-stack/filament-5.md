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

## Schemas & Layout Components
- **Namespaces:** In Filament v5, Layout components (like `Section`, `Grid`, `Fieldset`, `Card`) have been decoupled from Forms. They must be imported from `Filament\Schemas\Components\...` (e.g., `use Filament\Schemas\Components\Section;`).
- **Input Fields:** Data entry components (like `TextInput`, `Select`, `Toggle`) remain in `Filament\Forms\Components\...`. Always check imports carefully to prevent "Class not found" errors.

## Static Property Type Hints (Fatal Errors)
- **Strict Invariance:** PHP enforces strict property type matching. When overriding static properties in a Resource (like `$navigationGroup`, `$navigationIcon`, `$modelLabel`), the type hint MUST match the parent `Filament\Resources\Resource` exactly.
- **Rule:** Do NOT use `?string` for these properties. You MUST use the exact union type defined in Filament. For example:
  - `protected static string|\UnitEnum|null $navigationGroup = 'Settings';`
  - `protected static string|BackedEnum|null $navigationIcon = Heroicon::OutlinedLanguage;`
  - `protected static ?string $modelLabel = 'Label';` (This one is `?string` in Filament).
