# Filament v4.x Architecture Rules

## 1. RESOURCE DESIGN
- **Layout Organization:** Use **Clusters** to group related resources and pages. Navigation should be sorted explicitly via the `getNavigationSort()` method.
- **Read-Only Data:** Use **InfoLists** for displaying record details instead of read-only forms to provide a cleaner, faster user interface.
- **Custom Actions:** Implement logic in **Actions** (Resource actions, Header actions) rather than overriding controller methods.

## 2. FORM & TABLE OPTIMIZATION
- **Form Chaining:** Forms and Tables must exclusively use fluent chaining with strict static analysis (PHPStan Level 8) compliance.
- **Performance:** All Tables MUST use `eagerLoad()` for relationships to prevent N+1 queries.
- **Polling:** Polling interval should be managed carefully to avoid server overhead. Prefer `seconds(30)` or more.

## 3. ADVANCED PATTERNS
- **Property Hooks:** Use PHP 8.4 property hooks for managing computed states in custom widgets and pages.
- **Multi-Tenancy:** Always use Filament's native multi-tenancy features when the application requires scoped data access.
- **State Management:** Use `Alpine.js` (see `alpine-3.md`) for complex client-side interactions within Filament components.