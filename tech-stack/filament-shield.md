# Filament Shield Standards

## 1. INTEGRATION
- **Resource Security:** Automatically generate permissions for all Resources and Pages.
- **Base Policy:** Ensure all Resources use the `HasShield` trait or follow the Shield policy pattern.

## 2. ROLE MANAGEMENT
- **Super Admin:** Define a `super_admin` role that bypasses all permission checks.
- **Navigation:** Use Shield to hide/show navigation items based on user permissions.

## 3. BEST PRACTICES
- **Custom Permissions:** For actions beyond CRUD, register custom permissions in the Shield config.
- **Syncing:** Run `php artisan shield:generate` whenever new resources or pages are added.
