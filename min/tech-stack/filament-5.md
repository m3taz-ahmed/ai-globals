<RULE[filament-5]>
REQ: Livewire v4, PHP 8.2+
ISLANDS: indep render. NO waterfalls. Deferred filters v5.2.0+.
ASYNC: `->deferLoading()` dashboards/tables. Updates via Reverb/SSE. NO polling.
EMBEDS: v4 hooks `@script`, `@assets`. Scoped isolation. NO global leaks.
STATE: Use PHP Enums. State < 50KB or Redis. Scalar IDs only. NO full models.
SEC: Def-deny. `canViewAny`, `canCreate`, `canEdit`, `canDelete`, `canView`. Shield required.
SCHEMAS (CRITICAL): Filament v5 decoupled Layouts.
- Layouts (`Section`, `Grid`, `Fieldset`, `Card`) -> `Filament\Schemas\Components\...`
- Inputs (`TextInput`, `Select`, `Toggle`) -> `Filament\Forms\Components\...`
NO mismatch.
</RULE[filament-5]>
