[TECH] okta
[OBJ] Okta identity platform — OIDC, SAML, SCIM provisioning, API Access Management, Okta Verify, inline hooks, event hooks.
[RULES]
1. [REQ] Use OIDC authorization code flow with PKCE for all web and mobile applications; configure Okta as the OIDC IdP with `authorization_code` grant type and proper redirect URI allow-lists.
2. [REQ] Validate ID tokens and access tokens server-side by verifying the RS256 signature against the Okta JWKS endpoint (`/{org}/oauth2/{authServer}/v1/keys`); cache JWKS with TTL and refresh on `kid` mismatch.
3. [REQ] Use API Access Management (Authorization Servers) for custom OAuth scopes and claims; create custom authorization servers per API or audience — never use the org authorization server for custom API claims.
4. [REQ] Implement SCIM 2.0 provisioning for user lifecycle management; configure inbound SCIM from Okta to your app via the App Integration provisioning tab and handle `POST /Users`, `GET /Users`, `PATCH /Users`.
5. [REQ] Use Okta Verify as the primary MFA factor; configure push-based verification and TOTP as fallback; enforce MFA via authentication policies per application.
6. [REQ] Register inline hooks for real-time pre/post authentication logic (e.g., `com.okta.authentication.pre`); return JSON responses with `commands` array to modify the authentication flow.
7. [REQ] Register event hooks for async lifecycle events (e.g., `user.lifecycle.create`, `session.end`); verify the Okta webhook signature header (`x-okta-signature`) using HMAC-SHA256 with the shared secret.
8. [REQ] Use Okta session tokens (`sessionToken`) for embedded authentication flows only; never expose session tokens to the browser — exchange them immediately for OIDC tokens via the `/token` endpoint.
9. [REQ] Map Okta groups to application roles via group claims in the authorization server claim rules; use Okta groups for RBAC and assign users to groups, not individual app roles.
10. [REQ] Handle rate limiting (429 responses) with exponential backoff and jitter; Okta enforces per-org and per-endpoint rate limits — monitor via the System Log API.
11. [PROHIBIT] Never store Okta API tokens in client-side code or public repositories; never use the SSWS (SSWS token) header for user-facing authentication — use OAuth/OIDC flows.
12. [PROHIBIT] Never accept tokens without verifying `iss`, `aud`, `exp`, `cid`, and `kid`; never bypass MFA policies for privileged accounts in production.
[COMPAT]
- Okta Identity Engine (OIE) 2024.x: Modern authentication pipeline, policy-based MFA, Okta Verify push.
- Classic Engine is deprecated — migrate all apps to OIE.
- SDKs: `@okta/okta-auth-js` (v7.x), `@okta/okta-react` (v6.x), `okta-jwt-verifier` (Java/Node).
[REFS]
- https://developer.okta.com/docs/
- https://developer.okta.com/docs/guides/
- https://developer.okta.com/docs/reference/api/scim/
- https://developer.okta.com/docs/concepts/event-hooks/
- https://developer.okta.com/docs/concepts/inline-hooks/
