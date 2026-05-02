# Spatie Laravel Permission Standards

## 1. CONFIGURATION
- **Middleware:** Use `role` and `permission` middleware in routes.
- **Caching:** Ensure `permission.cache` is enabled in production. Run `artisan permission:cache-reset` during deployments.

## 2. USAGE PATTERNS
- **Checks:** Use Laravel's native `can()` and `@can` instead of `$user->hasPermissionTo()`.
- **Gates:** Rely on the automatic gate registration.
- **Seeding:** Use dedicated PermissionSeeders. Define roles/permissions in code, never manually in the database.

## 3. BEST PRACTICES
- **Role-Based vs Permission-Based:** Favor permission-based checks (`can('edit-articles')`) over role-based checks (`hasRole('editor')`) for better flexibility.
- **Direct Permissions:** Avoid assigning permissions directly to users; always assign to roles for maintainability.
