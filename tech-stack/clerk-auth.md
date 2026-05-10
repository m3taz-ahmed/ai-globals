# Tech-Stack: Clerk Auth

> [!NOTE]
> **TRIGGER:** LOAD ON authentication, user management, API security.
> **SCOPE:** Clerk integration for Next.js and Laravel 12/13.

## 1. Next.js Integration
- Wrap the application in `<ClerkProvider>`.
- Use Clerk's pre-built UI components (`<SignIn>`, `<UserButton>`) for rapid implementation, customized via CSS variables.
- Utilize Clerk middleware to protect routes on the edge.

## 2. Laravel 12/13 Integration
- Verify Clerk JWTs on Laravel API endpoints using native middleware and form requests.
- Synchronize Clerk user data to the local PostgreSQL database via Clerk Webhooks (`user.created`, `user.updated`, `user.deleted`).
- Handle session synchronization seamlessly across domains if necessary.

## 3. Authorization & Roles
- Integrate Clerk's user identity with Spatie Permission in Laravel for fine-grained Role-Based Access Control (RBAC).
- Store tenant IDs or specific app metadata in Clerk's `publicMetadata`.

## 4. Hard Constraints
- NEVER trust client-side data for authorization; always verify the Clerk JWT on the backend.
- NEVER process webhooks without verifying the Svix signature to prevent spoofing.
- ALWAYS use HTTPS for webhook endpoints.

---

## ✅ CLERK AUTH COMPLIANCE CHECK (Mandatory)
- [ ] **Verification:** Are all API requests verifying the Clerk JWT securely?
- [ ] **Webhooks:** Is Svix signature verification implemented for all Clerk webhooks?
- [ ] **RBAC:** Is the Clerk user identity correctly mapped to Spatie permissions?
