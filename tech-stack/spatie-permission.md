[TECH] spatie-permission
[OBJ] Spatie Laravel Permission Standards.
[RULES]
1. [REQ] Config: `role` / `permission` middleware. Enable `permission.cache` in prod.
2. [REQ] Usage: Native `can()` / `@can`. ⛔ NO `$user->hasPermissionTo()`.
3. [REQ] Seeding: PermissionSeeders in code. ⛔ NEVER manually in DB.
4. [REQ] Best Practice: Favor permission checks > role checks. Assign to Roles, NOT directly to Users.
