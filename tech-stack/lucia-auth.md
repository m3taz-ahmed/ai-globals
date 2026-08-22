[TECH] lucia-auth
[OBJ] Lucia Auth — session management, adapters, OAuth, database sessions, Astro/Next.js/SvelteKit integration, Lucia v3.
[RULES]
1. [REQ] Use Lucia v3 with the adapter pattern; initialize `Lucia` with a database adapter (e.g., `better-sqlite3`, `@libsql/client`, `pg`, `mongodb`) that implements `getUsers`, `getSessions`, `setSessions`, `deleteSessions`.
2. [REQ] Store sessions in the database (not JWTs); Lucia uses opaque session tokens — generate via `generateSessionToken()` and store the hash in the database, never the raw token.
3. [REQ] Define user attributes via `getUserAttributes` config and session attributes via `getSessionAttributes`; never store sensitive data in session attributes — keep them minimal.
4. [REQ] For OAuth integration, use the `@lucia-auth/oauth` package; configure providers (Google, GitHub, Discord, etc.) with `clientId`, `clientSecret`, `redirectUri`, and `scope` — handle the callback with `validateOAuthResponse`.
5. [REQ] Set session cookies via `setSessionCookie()` with `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for same-site apps); use `deleteSessionCookie()` on logout.
6. [REQ] Validate sessions on every request via `validateSessionToken()`; handle expired sessions by deleting them from the database and clearing the cookie — never extend sessions without explicit refresh logic.
7. [REQ] For Astro integration, use `defineMiddleware` to validate the session and pass `locals.user` and `locals.session`; for Next.js, use server components or route handlers with the App Router.
8. [REQ] For SvelteKit integration, use `locals` in `hooks.server.ts` to validate sessions; call `event.locals.validate()` in `+layout.server.ts` and pass user data to page data.
9. [REQ] Implement session expiration with `expires_at` column; Lucia checks expiration on validation — set `sessionCookie.expires` to match the database expiration for consistency.
10. [REQ] Handle the Lucia v3 migration from v2: replace `lucia()` with `new Lucia()` class instantiation, update adapter imports, and migrate from `getSessionUser` to `getSession` + `getUser`.
11. [PROHIBIT] Never store raw session tokens in the database — always store the SHA-256 hash via `generateSessionToken()` + `hashToken()`; never expose session tokens to client-side JavaScript.
12. [PROHIBIT] Never use JWT-based sessions with Lucia — the library is designed for database sessions; never skip `validateSessionToken()` on protected routes.
[COMPAT]
- v3.x (2024): Adapter-based architecture, class-based `Lucia` initialization, `@lucia-auth/oauth` v3.x.
- v2.x is deprecated — migrate to v3 (breaking changes in session API and adapter interface).
- Adapters: `@lucia-auth/adapter-sqlite`, `@lucia-auth/adapter-postgresql`, `@lucia-auth/adapter-mongodb`.
[REFS]
- https://lucia-auth.com/
- https://lucia-auth.com/getting-started/
- https://lucia-auth.com/guides/oauth/
- https://lucia-auth.com/integrations/astro/
- https://lucia-auth.com/integrations/sveltekit/
