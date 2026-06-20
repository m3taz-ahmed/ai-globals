[TECH] clerk-auth
[OBJ] Clerk Authentication & Authorization Integration.
[RULES]
1. [REQ] Next.js: `<ClerkProvider>`. Pre-built UI components. `clerkMiddleware()` for edge protection. Server-side `auth()`.
2. [REQ] Laravel: Verify JWTs on API endpoints. Sync local PostgreSQL via Clerk Webhooks (`user.created` etc). Map `sub` to `clerk_id`.
3. [REQ] Multi-Tenancy: Map Clerk Organizations to tenants. Sync via Webhooks. Store tenant config in Organization `publicMetadata`.
4. [REQ] Authorization: Integrate Clerk identity with Spatie Permission. Verify roles on backend.
5. [PROHIBIT] Hard Constraints: NEVER trust client-side data for auth. Verify Svix signature for webhooks. NEVER store PII/secrets in `publicMetadata` (use `privateMetadata`).
