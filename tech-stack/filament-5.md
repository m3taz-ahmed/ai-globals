# Filament v5.x Architecture Rules
- **Async First:** Leverage full asynchronous loading for all dashboard widgets and heavy table queries to achieve 0ms UI blocking.
- **Component Embeds:** When injecting native Vue 3 or custom external JS components into Filament views, strictly adhere to the updated Livewire lifecycle hooks.
- **State:** Manage internal UI state using native PHP 8.5 Enums mapped directly to Filament Actions.