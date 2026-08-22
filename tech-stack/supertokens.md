[TECH] supertokens
[OBJ] SuperTokens open-source authentication — core, recipes, session management, social login, multi-tenancy, email password, passwordless.
[RULES]
1. [REQ] Deploy the SuperTokens Core as a separate service (Docker or self-hosted) and connect the backend SDK to it via the `connectionURI`; never embed the Core logic in the application process.
2. [REQ] Use the EmailPassword recipe for traditional auth with password hashing handled by the Core; never hash passwords in application code — delegate to the Core's `signUp` and `signIn` APIs.
3. [REQ] Use the Session recipe with refresh token rotation; the frontend SDK automatically handles access token refresh via the `/refresh` endpoint — never store access tokens in localStorage without the SDK managing rotation.
4. [REQ] Configure CORS on the backend to allow only your frontend origin; the SuperTokens middleware must be placed before all route handlers to intercept session refresh and sign-out requests.
5. [REQ] For social login, use the ThirdParty recipe with configured providers (Google, GitHub, Apple, etc.); map provider user info to SuperTokens user IDs and merge with existing email-password accounts via `signInUp` hooks.
6. [REQ] For passwordless auth (magic links or OTP), use the Passwordless recipe; configure `codeLifetime` and `linkLifetime` appropriately and rate-limit resend requests to prevent abuse.
7. [REQ] For multi-tenancy, use the `MultiTenancy` recipe with `createNewTenant` and `associateUserWithTenant`; configure tenant-specific third-party providers and email/password configs per tenant.
8. [REQ] Implement session revocation via `revokeSession` and `revokeAllSessionsForUser`; use `getSession` with `antiCsrfCheck` enabled for state-changing operations.
9. [REQ] Override recipe functions via `override` config for custom logic (e.g., custom email sending, post-signup hooks); never modify the Core source directly.
10. [REQ] Handle Core errors with proper status codes; the SDK throws `SuperTokensError` with `type` — map `WRONG_CREDENTIALS_ERROR`, `EMAIL_ALREADY_EXISTS_ERROR`, etc. to user-facing messages.
11. [PROHIBIT] Never expose the Core API directly to the frontend without the SDK middleware; never disable CSRF protection for session-based auth in browser contexts.
12. [PROHIBIT] Never store raw passwords or password hashes in the application database — the Core manages credential storage; never use `antiCsrfCheck: false` for state-changing endpoints.
[COMPAT]
- Core v9.x (2024): Multi-tenancy GA, passwordless improvements, PostgreSQL and MongoDB backends.
- SDKs: `supertokens-node` (v18.x), `supertokens-python` (v0.x), `supertokens-web-js` (v0.x), `supertokens-auth-react` (v0.x).
[REFS]
- https://supertokens.com/docs
- https://supertokens.com/docs/quickstart/backend-setup
- https://supertokens.com/docs/recipes/session
- https://supertokens.com/docs/recipes/multitenancy
- https://supertokens.com/docs/concepts/architecture
