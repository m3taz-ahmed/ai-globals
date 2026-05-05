# Tech-Stack: SaaS Multi-Tenancy

## Laravel Implementation (`stancl/tenancy`)
- **Initialization:** Use `Tenancy::initialize($tenant)` middleware.
- **Database:** Automatic DB/Schema switching via package drivers.
- **Cache:** Tenant-prefixed Redis/Cache store.
- **Filesystem:** `Storage::disk('tenant')` for isolated uploads.

## Next.js Implementation
- **Middleware:** Subdomain/Custom domain resolution.
- **Context:** Inject `x-tenant-id` in request headers.
- **Switching:** Clear all client-side caches on tenant switch.
- **Layouts:** Shared dashboard shell with tenant-specific branding.

## Constraints
- NEVER use global variables for tenant context.
- ALWAYS propagate tenant context to background jobs.
- Validate tenant ownership on every state-changing request.
