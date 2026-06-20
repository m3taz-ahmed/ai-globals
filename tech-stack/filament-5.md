[TECH] filament-5
[OBJ] Filament v5.x Architecture Rules.
[RULES]
1. [REQ] Islands: Livewire v4 independent renders. ⛔ waterfalls. Deferred filters for heavy queries.
2. [REQ] Async/Defer: `->deferLoading()`. Reverb/SSE for real-time. ⛔ client-side polling.
3. [REQ] Components: Scoped styles. v4 hooks (`@script`, `@assets`).
4. [REQ] State: PHP Enums for UI state. State < 50KB (Redis otherwise). Pass scalar IDs (⛔ full models).
5. [REQ] Static Props (Fatal Error Fix): Match exact union types when overriding static properties (e.g. `protected static string|BackedEnum|null $navigationIcon`). NO `?string`.
