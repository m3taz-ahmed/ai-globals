# Tech-Stack: Clerk Auth

> [!NOTE]
> **TRIGGER:** LOAD ON authentication, user management, API security, organization management.
> **SCOPE:** Clerk integration for Next.js and Laravel 12/13, Organizations, multi-tenant SaaS.

## 1. Next.js Integration
- Wrap the application in `<ClerkProvider>`. Configure with `publishableKey` from environment variables.
- Use Clerk's pre-built UI components (`<SignIn>`, `<SignUp>`, `<UserButton>`, `<OrganizationSwitcher>`) for rapid implementation, customized via CSS variables and Tailwind.
- Utilize Clerk middleware (`clerkMiddleware()`) to protect routes on the edge. Use `authProtect()` for route-level guards.
- Use `auth()` server-side for session data and `currentUser()` for full user object. Prefer `auth()` for lightweight checks (avoids API call overhead).

## 2. Laravel 12/13 Integration
- Verify Clerk JWTs on Laravel API endpoints using native middleware and form requests.
- Synchronize Clerk user data to the local PostgreSQL database via Clerk Webhooks (`user.created`, `user.updated`, `user.deleted`).
- Handle session synchronization seamlessly across domains if necessary.
- Map the Clerk JWT `sub` claim to the local `users.clerk_id` column for identity correlation.

## 3. Organizations & Multi-Tenancy
- Leverage Clerk **Organizations** for multi-tenant SaaS: each organization maps to a tenant in the backend.
- Use `<OrganizationSwitcher>` to allow users to navigate between tenants without custom UI.
- Store tenant-level configuration in Clerk's Organization `publicMetadata` (e.g., `tenant_id`, `plan`, `region`).
- Sync organization lifecycle via Webhooks (`organization.created`, `organization.updated`, `organization.deleted`) to the local `tenants` table.
- Use Organization membership roles (`org:admin`, `org:member`) to map to Spatie Permission roles in Laravel.
- Configure organization invitations via Clerk's built-in flow; do not build custom invitation logic.

## 4. Authorization & Roles
- Integrate Clerk's user identity with Spatie Permission in Laravel for fine-grained Role-Based Access Control (RBAC).
- Store user-level metadata in Clerk's `publicMetadata` (e.g., `role`, `tenant_id`).
- Use Clerk's `createAuthority()` or custom claims for backend authorization decisions.
- NEVER rely solely on frontend role checks; always verify on the backend.

## 5. Session & Token Management
- Configure session token refresh strategy: use Clerk's automatic token rotation (default 60s refresh for short-lived tokens).
- Pass the Clerk session token in the `Authorization: Bearer` header for all API calls from Next.js to Laravel.
- Handle token expiration gracefully on the frontend with Clerk's `useAuth()` hook for reactive session state.

## 6. Hard Constraints
- NEVER trust client-side data for authorization; always verify the Clerk JWT on the backend.
- NEVER process webhooks without verifying the Svix signature to prevent spoofing.
- ALWAYS use HTTPS for webhook endpoints.
- NEVER build custom organization/invitation flows when Clerk Organizations can handle it natively.
- NEVER store sensitive data (PII, secrets) in Clerk `publicMetadata` — it is readable client-side. Use `privateMetadata` for server-only data.

---

## ✅ CLERK AUTH COMPLIANCE CHECK (Mandatory)
- [ ] **Verification:** Are all API requests verifying the Clerk JWT securely?
- [ ] **Webhooks:** Is Svix signature verification implemented for all Clerk webhooks?
- [ ] **RBAC:** Is the Clerk user identity correctly mapped to Spatie permissions?
- [ ] **Organizations:** Are Clerk Organizations used for multi-tenant isolation with webhook sync?
- [ ] **Metadata Safety:** Is sensitive data kept out of `publicMetadata` (using `privateMetadata` instead)?
