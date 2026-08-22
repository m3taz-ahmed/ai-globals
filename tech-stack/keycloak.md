[TECH] keycloak
[OBJ] Keycloak open-source identity and access management — realms, clients, roles, groups, federated identity, custom providers, Keycloak Operator, token exchange.
[RULES]
1. [REQ] Use separate realms per tenant or environment; never share a single realm across production and non-production environments.
2. [REQ] Configure clients with `confidential` access type for server-side apps and `public` access type only for SPAs/mobile with PKCE enforced; always set `frontchannelLogout` and proper redirect URIs.
3. [REQ] Map realm roles and client roles into JWT claims via protocol mappers; use `realm_access.roles` and `resource_access.<client>.roles` for authorization decisions on the backend.
4. [REQ] Use groups for hierarchical role assignment; assign roles to groups and users inherit via group membership — avoid per-user role assignment at scale.
5. [REQ] For federated identity (LDAP, Active Directory), configure User Federation with sync mode `FORCE` for read-only or `SYNC` for bidirectional; cache LDAP queries with the realm cache enabled.
6. [REQ] Implement custom identity providers (OIDC/SAML) via SPI providers packaged as JAR modules in `providers/` directory; register via `kcadm.sh` or the Admin REST API.
7. [REQ] Use the Keycloak Operator on Kubernetes/OpenShift for declarative realm and client management via `KeycloakRealmImport` CRDs; never manually configure production realms through the admin UI alone.
8. [REQ] For token exchange (RFC 8693), enable the `token-exchange` feature flag and use the `grant_type=urn:ietf:params:oauth:grant-type:token-exchange` flow for impersonation and delegation scenarios.
9. [REQ] Validate access tokens using the realm JWKS endpoint (`/realms/{realm}/protocol/openid-connect/certs`); verify `iss`, `aud`, `exp`, and `typ` claims server-side.
10. [REQ] Use refresh token rotation with `revokeRefreshToken=true` and `refreshTokenMaxReuse=0` to detect token theft; implement a revocation endpoint for logout.
11. [PROHIBIT] Never expose the admin realm (`master`) to end-user applications; never use the master realm for application clients.
12. [PROHIBIT] Never disable HTTPS/SSL in production; never set `sslRequired=none` outside local development; never store user passwords in `userMetadata` — use the built-in credential store.
[COMPAT]
- v25.x (2024): Quarkus-based distribution, Jakarta EE namespace, Operator v25.x for K8s.
- v26.x (2025): Token Exchange GA, improved multi-tenant support, OIDC 1.0 certified.
- Legacy WildFly distribution (<= v17) is EOL — migrate to Quarkus distribution.
[REFS]
- https://www.keycloak.org/documentation
- https://www.keycloak.org/docs/latest/server_admin/
- https://www.keycloak.org/docs/latest/securing_apps/
- https://www.keycloak.org/operator/
- https://www.keycloak.org/docs/latest/securing_apps/#token-exchange
