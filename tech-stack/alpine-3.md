# Alpine.js v3.x Standards

## 1. COMPONENT DESIGN
- **Self-Contained:** Keep logic inside the `x-data` attribute for simple components.
- **Global Stores:** Use `Alpine.store()` for state that needs to be shared across multiple components.

## 2. REACTIVITY
- **Directives:** Use `x-show`, `x-if`, and `x-for` efficiently. Prefer `x-show` (CSS display) over `x-if` (DOM removal) for frequently toggled elements.
- **Events:** Use `x-on` (or `@`) for event handling. Use `.prevent`, `.stop`, and `.window` modifiers where appropriate.

## 3. INTEGRATION WITH LIVEWIRE
- **Entangle:** Use `$wire.entangle()` to sync Alpine.js state with Livewire properties.
- **Ignore:** Use `wire:ignore` on elements where Alpine.js manages complex DOM manipulations to prevent Livewire from overriding them.
