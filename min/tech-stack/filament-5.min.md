[FILAMENT_V5]
REQ: Livewire v4, PHP 8.2+.
UI: Islands (indep renders) > no waterfalls. deferred filters (v5.2.0+).
ASYNC: ->deferLoading() or Islands. Reverb/SSE > no poll.
JS: LW v4 hooks (@script, @assets), scoped styles > no leak.
STATE: Enums > magic str. <50KB, Redis if big. Scalar IDs > no full models.
SEC: canViewAny/Create/Edit/Delete, bezhansalleh/filament-shield.
SCHEMAS: Layouts (Section,Grid) = Filament\Schemas\Components\. Inputs (Text,Select) = Filament\Forms\Components\.
TYPES: Static prop overrides MUST exactly match parent union (e.g. string|\UnitEnum|null). NO ?string if parent is union.
