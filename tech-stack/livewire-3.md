[TECH] livewire-3
[OBJ] Livewire 3.x Architecture Standards.
[RULES]
1. [REQ] Component: Single Responsibility. `kebab-case` in views, `PascalCase` in PHP. `#[Layout]` for full-page.
2. [REQ] Data Binding: `wire:model.blur` (default/preferred for forms). `wire:model.live` (sparingly, for search). `#[Computed]` for cached derived data.
3. [REQ] Performance: `#[Lazy]` for heavy comps. `wire:poll` with stop condition. Minimize public props for hydration payload.
4. [REQ] Alpine Interop: `$wire.entangle()`. Alpine for UI/client-state, Livewire for server-state.
5. [REQ] Events: `$this->dispatch()`. `#[On('event')]` handlers.
6. [REQ] Navigation: `wire:navigate` (SPA mode). `@persist` for surviving navigation.
