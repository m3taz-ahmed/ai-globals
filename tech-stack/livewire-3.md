# Livewire 3.x Architecture Standards

## 1. COMPONENT DESIGN
- **Single Responsibility:** Each Livewire component should handle ONE concern. Split complex pages into nested child components.
- **Naming Convention:** Components must follow `kebab-case` in views (`<livewire:booking-table />`) and `PascalCase` in PHP classes (`BookingTable`).
- **Full-Page Components:** Use Livewire full-page components with `#[Layout('layouts.app')]` attribute for standalone pages.

## 2. DATA BINDING & REACTIVITY
- **`wire:model.live`:** Use for real-time reactivity (search fields, filters). Adds a network request on every keystroke — use sparingly.
- **`wire:model.blur`:** Prefer for form inputs where instant feedback is not needed. Reduces server round-trips.
- **`wire:model` (default):** Deferred binding — syncs on form submission. Use for standard forms.
- **Computed Properties:** Use `#[Computed]` attribute for derived data. Results are cached for the request lifecycle.

## 3. PERFORMANCE
- **Lazy Loading:** Use `#[Lazy]` attribute on heavy components to defer rendering until visible in the viewport.
- **Polling:** Use `wire:poll.30s` with caution. Always include a condition to stop polling when data is stale or the user is inactive.
- **Pagination:** Use Livewire's built-in pagination. Avoid loading all records into component state.
- **Hydration:** Minimize public properties. Large arrays/objects in component state increase hydration payload.

## 4. ALPINE.JS INTEROP
- **`@entangle`:** Use `$wire.entangle('property')` to synchronize Livewire properties with Alpine.js state bidirectionally.
- **`$wire`:** Access Livewire methods from Alpine.js via `$wire.methodName()`. Avoid direct DOM manipulation.
- **Separation:** Use Alpine for client-side-only interactions (toggles, animations, dropdowns). Use Livewire for server-side state changes.

## 5. EVENTS & COMMUNICATION
- **Dispatch:** Use `$this->dispatch('event-name', data: $value)` for component-to-component communication.
- **Listen:** Use `#[On('event-name')]` attribute on handler methods. Avoid `protected $listeners` array (legacy).
- **Browser Events:** Use `$this->dispatch('event-name')->to(Component::class)` for targeted communication. Broadcast to browser with `$this->dispatch('event-name')->self()`.

## 6. NAVIGATE & SPA MODE
- **`wire:navigate`:** Add to all internal links for SPA-like navigation without full page reloads.
- **`@persist`:** Use `@persist('key')` directive for elements that should survive navigation (audio players, sidebars).
- **Prefetching:** `wire:navigate` prefetches pages on hover. Ensure controllers/components handle prefetch requests efficiently.
