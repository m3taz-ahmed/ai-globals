[TECH] filament-4
[OBJ] Filament v4.x Architecture Rules.
[RULES]
1. [REQ] Design: Group via Clusters. `InfoLists` for read-only data. Custom logic in Actions.
2. [REQ] Optimization: Fluent chaining only (PHPStan Lvl 8). `eagerLoad()` on ALL tables. Polling >30s.
3. [REQ] Structure: Use PHP 8.4 property hooks. Use Filament native multi-tenancy.
4. [REQ] Custom Namespaces: Use `Filament\Schemas\Components` (NOT `Filament\Forms\...`). Use `configure()` from Schema classes.
