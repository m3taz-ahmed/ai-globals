[TECH] saas-tenancy
[OBJ] SaaS Multi-Tenancy (stancl/tenancy, Next.js).
[RULES]
1. [REQ] Laravel: `Tenancy::initialize()`. Automatic DB/Schema switching. Prefix Cache/Filesystem per tenant. `Tenancy::runForMultiple()` for jobs.
2. [REQ] Next.js: `x-tenant-id` header validation. Clear caches (Zustand/Query) on switch.
3. [PROHIBIT] Hard Constraints: NEVER cross tenant boundaries (always `where('tenant_id')`). NEVER trust client-side tenant claims. Provision via DB transactions.
