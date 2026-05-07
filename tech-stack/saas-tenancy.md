# Tech-Stack: SaaS Multi-Tenancy

> [!NOTE]
> **TRIGGER:** LOAD ON TENANT ARCHITECTURE, SCOPING, OR DATA ISOLATION TASKS.
> **SCOPE:** LARAVEL (STANCL/TENANCY), NEXT.JS, AND CROSS-STACK PATTERNS.

## 1. Laravel Implementation (`stancl/tenancy`)
- **Initialization:** Use `Tenancy::initialize($tenant)` middleware. Register `InitializeTenancyByDomain` or `InitializeTenancyByPath` as route middleware.
- **Database:** Automatic DB/Schema switching via package drivers. Use `database()` for separate DB, `schema()` for separate schema per tenant.
- **Cache:** Tenant-prefixed Redis/Cache store via `cache()->store('tenant')`.
- **Filesystem:** `Storage::disk('tenant')` for isolated uploads. Configure `tenant` disk in `config/filesystems.php` with dynamic path resolution.
- **Queue Scoping:** Use `Tenancy::runForMultiple()` for tenant-aware job processing. Always tag queued jobs with `tenant_id`.
- **Events:** Listen to `TenantInitialized`, `TenantSwitched`, `TenantEnded` for cross-cutting concerns (logging, cache warming).

## 2. Next.js Implementation
- **Middleware:** Subdomain/Custom domain resolution via Next.js middleware.
- **Context:** Inject `x-tenant-id` in request headers. Validate on server-side.
- **Switching:** Clear all client-side caches (TanStack Query, Zustand) on tenant switch.
- **Layouts:** Shared dashboard shell with tenant-specific branding (logo, colors, domain).
- **API Routes:** All API routes must validate `x-tenant-id` header and scope queries accordingly.

## 3. Cross-Stack Patterns
- **Central Auth:** Shared authentication service (Sanctum/JWT) with tenant-aware token claims.
- **API Gateway:** Route requests to correct tenant context based on domain/header.
- **Data Migration:** Tenant onboarding must handle schema provisioning, seed data, and default configuration asynchronously.

## 4. Hard Constraints
- NEVER use global variables for tenant context. Use the package's resolver or middleware.
- ALWAYS propagate tenant context to background jobs, events, and notifications.
- Validate tenant ownership on every state-changing request — never trust client-side tenant claims.
- NEVER cross-tenant data boundaries in queries. Every Eloquent query in a scoped model MUST include `where('tenant_id', ...)`.
- ALWAYS use database transactions for tenant creation (provisioning must be atomic).

## 5. Testing Multi-Tenancy
- Test tenant isolation: create data in Tenant A, verify Tenant B cannot access it.
- Test tenant initialization: verify middleware correctly sets tenant context.
- Test concurrent tenant operations: ensure cache and queue isolation.
- Test tenant provisioning: verify schema/DB creation, seeding, and rollback.

---

## ✅ TENANCY COMPLIANCE CHECK (Mandatory)
- [ ] **Scoping:** Does every new query/model include a `tenant_id` scope?
- [ ] **Provisioning:** Is tenant creation handled asynchronously with proper error recovery?
- [ ] **Isolation:** Can Tenant A NEVER access Tenant B's data?
- [ ] **Jobs:** Are all queued jobs tenant-aware with proper context propagation?
- [ ] **Cache:** Is tenant-specific cache properly prefixed and cleared on switch?
