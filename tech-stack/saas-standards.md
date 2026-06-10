# SaaS Architectural Standards
> [!NOTE]
> **TRIGGER:** LOAD ON TENANT ARCHITECTURE, SUBSCRIPTION, OR MULTI-TENANCY TASKS.
> **SCOPE:** TENANCY MODELS, BILLING, AND ENTERPRISE SECURITY.

## 1. Tenancy Model Decision Matrix
Before implementation, evaluate based on these signals:

| Signal | Shared Schema | Separate Schema | Separate DB |
|---|---|---|---|
| Tenants > 1000 | ✅ Recommended | ⚠️ Viable | ❌ Too costly |
| Tenants 50-500 | ⚠️ Viable | ✅ Recommended | ⚠️ Viable |
| Tenants < 50 | ❌ Risky | ⚠️ Viable | ✅ Recommended |
| High Compliance | ❌ Forbidden | ⚠️ Viable | ✅ Recommended |

## 2. Shared Schema (Single DB) [SaaS-01]
- **Constraint:** Every model MUST use `BelongsToTenant` trait.
- **Security:** Enforce tenant isolation at the application level using global scopes (e.g., `BelongsToTenant` trait). Note: MySQL does not support native Row-Level Security — application-level enforcement is required.
- **Indexing:** `tenant_id` MUST be indexed on all scoped tables.

## 3. Separate Schema/DB [SaaS-02]
- **Automation:** Provisioning MUST be asynchronous (Queue).
- **Migration:** Use parallelized migration runners.
- **Cleanup:** Implement automated data purging/offboarding.

## 4. Enterprise Security [SaaS-03]
- **SSO/SAML:** Tenant-aware IdP discovery by email domain.
- **RBAC:** Roles and permissions MUST be scoped per tenant.
- **Audit:** Activity logs MUST include `tenant_id`.

## 5. Billing & Onboarding [SaaS-04]
- **Source of Truth:** External gateway (Stripe/Paddle) is the master.
- **Webhooks:** Mandatory for state synchronization.
- **TTV:** Minimize steps to first value (< 30s provisioning).

---

## 🏢 SAAS COMPLIANCE CHECK (Mandatory)
- [ ] **Scoping:** Does every new query/model include a `tenant_id` scope? [SaaS-01]
- [ ] **Provisioning:** Is the tenant creation process handled asynchronously? [SaaS-02]
- [ ] **Security:** Are roles/permissions verified to be tenant-isolated? [SaaS-03]
- [ ] **Billing:** Is the feature gated correctly based on the tenant's subscription? [SaaS-04]
