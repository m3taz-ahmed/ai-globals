[TECH] filament-3
[OBJ] Filament v3 Best Practices.
[RULES]
1. [REQ] Performance: Optimize `query()`. Avoid `$appends` on Models. Use `deferLoading()` for heavy widgets.
2. [REQ] UX: Use native Actions over custom livewire components. Action modals in tables preserve state.
3. [REQ] Customization: Override views cleanly. Extract massive schemas to standalone methods.
