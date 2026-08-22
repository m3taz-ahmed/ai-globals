[TECH] auth0
[OBJ] Auth0 identity platform — OIDC, SAML, MFA, rules, actions, organizations, B2B, M2M, social login, JWKS caching.
[RULES]
1. [REQ] Use OIDC authorization code flow with PKCE for all SPA and mobile applications; never use implicit flow for new apps.
2. [REQ] Validate ID tokens and access tokens on the backend by verifying the RS256 signature against the JWKS endpoint; cache JWKS keys with a TTL of at least 10 minutes and refresh on `kid` mismatch.
3. [REQ] Migrate legacy Rules to Actions; Rules are deprecated and will be removed — all custom logic must be in Actions deployed via the Auth0 Deploy CLI or Management API.
4. [REQ] Use Organizations for B2B multi-tenancy; assign connection strategies per organization and enforce organization-specific branding and roles via organization-level claims.
5. [REQ] Enforce MFA via the `multifactor` prompt or step-up authentication; require MFA for privileged operations and expose `amr` (authentication methods reference) claims for policy decisions.
6. [REQ] For machine-to-machine (M2M) flows, use the Client Credentials grant with audience set to your API identifier; cache tokens until 80% of `exp` and rotate client secrets periodically.
7. [REQ] Store secrets and signing keys in Auth0 Secrets store or an external secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault); never hardcode secrets in Actions code.
8. [REQ] Implement social login via configured connections (Google, GitHub, etc.); map `user_metadata` and `app_metadata` carefully — never store PII in `user_metadata` as it is writable from the client.
9. [REQ] Verify Auth0 Management API tokens with the correct audience (`https://<tenant>.auth0.com/api/v2/`) and scope; use M2M tokens for backend Management API calls, never user tokens.
10. [REQ] Handle webhook/log events via Log Streams (not deprecated Rules); configure Log Streams to SIEM for audit and compliance.
11. [PROHIBIT] Never accept tokens without verifying `iss`, `aud`, `exp`, `iat`, and `kid` against the tenant's JWKS; never trust client-side token claims for authorization without server-side validation.
12. [PROHIBIT] Never disable the `require_pushed_authorization_requests` option in production; never use `HS256` signing for production tenants — use `RS256` or `PS256`.
[COMPAT]
- v2024.x: Actions GA, Rules deprecated (removal scheduled), Organizations GA, Pushed Authorization Requests (PAR) supported.
- Node.js SDK `auth0-js` deprecated; use `@auth0/auth0-react` for SPA, `@auth0/nextjs-auth0` for Next.js, `express-oauth2-jwt-bearer` for API validation.
[REFS]
- https://auth0.com/docs
- https://auth0.com/docs/get-started/auth0-overview
- https://auth0.com/docs/secure/tokens/json-web-tokens
- https://auth0.com/docs/customize/actions
- https://auth0.com/docs/manage-users/organizations
