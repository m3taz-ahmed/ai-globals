# Filament v4.x Architecture Rules
- **Property Hooks:** Use PHP 8.4 property hooks for managing computed states in custom widgets and pages.
- **Form Chaining:** Forms and Tables must exclusively use fluent chaining with strict static analysis (PHPStan Level 8) compliance.
- **Layout Organization:** Use **Clusters** to group related resources and pages. Navigation should be sorted explicitly via the `getNavigationSort()` method.
- **Performance:** All Tables MUST use `eagerLoad()` for relationships to prevent N+1 queries. Polling interval should be managed carefully to avoid server overhead.
- **Read-Only Data:** Use **InfoLists** for displaying record details instead of read-only forms to provide a cleaner, faster user interface.