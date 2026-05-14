# Filament v5.x Architecture Rules
> [!NOTE]
> **STATUS:** STABLE — Released January 2026. Requires Livewire v4 + PHP 8.2+.
> **TRIGGER:** LOAD ON ALL FILAMENT PANEL, RESOURCE, OR WIDGET TASKS.

## 1. LIVEWIRE v4 ISLANDS ARCHITECTURE (Core)
- **Independent Renders:** Filament v5 leverages Livewire v4 "Islands" for isolated component re-renders. A stats widget update MUST NOT trigger a full page re-render.
- **No Render Waterfall:** Large resource tables and chart widgets update independently. Never architect a page where one widget's state change causes all others to re-hydrate.
- **Deferred Filters:** For chart widgets with expensive queries, use deferred filter mode (v5.2.0+) — users batch changes before triggering a single server call.

## 2. ASYNC-FIRST ARCHITECTURE
- **Non-Blocking UI:** All dashboard widgets and heavy table queries MUST use `->deferLoading()` or Island-based async loading to achieve 0ms main-thread UI blocking.
- **Streaming:** Use Laravel Reverb (WebSockets) or SSE for real-time data updates (live order feeds, system metrics). Never use client-side polling intervals.

## 3. COMPONENT EMBEDS
- **External JS:** When injecting custom JS components into Filament views, strictly adhere to the Livewire v4 lifecycle hooks (`@script`, `@assets`).
- **Isolation:** External components MUST NOT leak global CSS or JS into the panel. Use scoped styles and module-pattern scripts with `@layer` for CSS encapsulation.

## 4. STATE MANAGEMENT
- **PHP 8.4+ Enums:** Manage internal UI state (action modes, filter states) using native PHP 8.4 Backed Enums mapped directly to Filament Actions. Never use magic strings for status values.
- **Session State:** NEVER store large datasets in Livewire component state. Use Redis-backed session or cache for any structure exceeding 50KB.
- **Model Binding:** Avoid serializing full Eloquent Models into Livewire state. Pass only scalar IDs; resolve models server-side.

## 5. SECURITY
- **Resource Authorization:** ALWAYS implement `canViewAny()`, `canCreate()`, `canEdit()`, `canDelete()`, and `canView()` on every Resource. Default deny unless explicitly granted.
- **Filament Shield:** Use `bezhansalleh/filament-shield` for role-based Filament panel access. Never hand-roll RBAC in panel code.

---

## ✅ FILAMENT v5 COMPLIANCE CHECK (Mandatory)
- [ ] **Islands:** Do widgets use Livewire v4 Islands to avoid render waterfalls?
- [ ] **Deferred Filters:** Are expensive chart filter operations deferred?
- [ ] **State Size:** Is Livewire component state under 50KB?
- [ ] **Authorization:** Do all Resources implement all 5 policy methods?
- [ ] **CSS Isolation:** Are injected external components using scoped styles?
