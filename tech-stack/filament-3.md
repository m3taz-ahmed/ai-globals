# Filament v3 Best Practices

## 1. PERFORMANCE FIRST
- Filament tables can become very slow with large datasets. Always optimize `query()` methods.
- Avoid heavy appended attributes (`$appends`) in Eloquent models used within Filament.
- Use `deferLoading()` on heavy widgets.

## 2. ACTIONS & MODALS
- Leverage Filament Actions instead of creating custom livewire components whenever possible.
- Use Action modals for complex form inputs directly within tables to preserve UX.

## 3. CUSTOMIZATION
- Override Views cleanly. If a custom Livewire component is needed within a Filament page, ensure it follows Filament's styling ecosystem (Tailwind).
- Keep Resources clean: extract massive form schemas or table schemas into standalone variables or methods.