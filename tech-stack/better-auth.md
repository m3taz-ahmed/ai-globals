[TECH] better-auth
[OBJ] Better Auth — TypeScript-first auth library, plugins, organization, rate limit, 2FA, passkey, OAuth, session caching.
[RULES]
1. [REQ] Initialize Better Auth with `betterAuth()` using a database adapter (Kysely, Drizzle, Prisma, or MongoDB); define `emailAndPassword` and `socialProviders` in the config — never hardcode provider secrets, use environment variables.
2. [REQ] Use the `organization` plugin for multi-tenancy; call `organization.create()`, `organization.addMember()`, and enforce organization-scoped access via `session.activeOrganizationId` — never query across organizations without explicit checks.
3. [REQ] Enable the `rateLimit` plugin with per-endpoint limits; configure `window` and `max` for auth endpoints (e.g., sign-in, sign-up, password reset) — use a persistent storage backend (Redis) in production, not in-memory.
4. [REQ] Enable the `twoFactor` plugin with TOTP as the primary method; store TOTP secrets encrypted at rest and verify via `twoFactor.verifyTotp()` — never accept backup codes without rate limiting the verification endpoint.
5. [REQ] Enable the `passkey` plugin for WebAuthn-based authentication; use `passkey.registerPasskey()` on the client and verify the attestation on the server — store credential public keys in the `passkey` table, never in user metadata.
6. [REQ] Configure OAuth providers (Google, GitHub, Apple, Discord, etc.) via `socialProviders` in the auth config; handle the callback via the `/callback/:provider` route and link accounts by email with `accountLinking` config.
7. [REQ] Use session caching via the `sessionCookie` config with `cache` enabled; set `maxAge` and `updateAge` to control session lifetime and refresh — cached sessions reduce database load on high-traffic apps.
8. [REQ] Handle Better Auth errors via the typed `APIError` class; check `error.status` and `error.body.code` (e.g., `INVALID_PASSWORD`, `USER_ALREADY_EXISTS`) and map to user-facing messages — never expose internal error details.
9. [REQ] Use the Better Auth client SDK (`createAuthClient()`) for frontend integration; call `signIn.email()`, `signUp.email()`, `signOut()` from the client — never make raw fetch calls to auth endpoints.
10. [REQ] Mount the Better Auth handler via `toNextJsHandler()`, `toNodeHandler()`, or `toSvelteKitHandler()` depending on the framework; the handler must be mounted before other middleware to intercept auth routes.
11. [PROHIBIT] Never store passwords in plaintext or with weak hashing — Better Auth uses Scrypt by default; never override the password hashing to a weaker algorithm.
12. [PROHIBIT] Never disable CSRF protection; never expose the `secret` or database connection string to the client; never skip session validation on protected API routes.
[COMPAT]
- v1.x (2024): TypeScript-first, plugin architecture, framework-agnostic handlers.
- Adapters: `better-auth/adapters/kysely`, `better-auth/adapters/drizzle`, `better-auth/adapters/prisma`, `better-auth/adapters/mongodb`.
- Frameworks: Next.js, SvelteKit, Nuxt, Astro, Hono, Express, Elysia.
[REFS]
- https://www.better-auth.com/docs
- https://www.better-auth.com/docs/concepts/plugins
- https://www.better-auth.com/docs/authentication/social
- https://www.better-auth.com/docs/concepts/session-management
- https://www.better-auth.com/docs/integrations
