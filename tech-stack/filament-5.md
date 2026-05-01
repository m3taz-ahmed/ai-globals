# Filament v5.x Architecture Rules
> [!SPECULATIVE] Filament v5 is not yet released. Rules are based on community previews and announced roadmap. Verify against official release notes before applying.

## 1. ASYNC-FIRST ARCHITECTURE
- **Non-Blocking UI:** Leverage full asynchronous loading for all dashboard widgets and heavy table queries to achieve 0ms UI blocking.
- **Streaming:** Use server-sent events or WebSocket channels for real-time data updates instead of polling where supported.

## 2. COMPONENT EMBEDS
- **External JS:** When injecting native Vue 3 or custom external JS components into Filament views, strictly adhere to the updated Livewire lifecycle hooks.
- **Isolation:** External components must not leak global CSS or JS. Use scoped styles and module-pattern scripts.

## 3. STATE MANAGEMENT
- **PHP Enums:** Manage internal UI state using native PHP 8.5 Enums mapped directly to Filament Actions.
- **Session State:** Avoid storing large datasets in Livewire component state. Use session or cache for data exceeding 50KB.