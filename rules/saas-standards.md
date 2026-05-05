# SaaS Architectural Standards

## 1. Tenancy Model Decision Matrix
Before implementation, evaluate based on these signals:

| Signal | Shared Schema | Separate Schema | Separate DB |
|---|---|---|---|
| Tenants > 1000 | ✅ Recommended | ⚠️ Viable | ❌ Too costly |
| Tenants 50-500 | ⚠️ Viable | ✅ Recommended | ⚠️ Viable |
| Tenants < 50 | ❌ Risky | ⚠️ Viable | ✅ Recommended |
| High Compliance | ❌ Forbidden | ⚠️ Viable | ✅ Recommended |

## 2. Shared Schema (Single DB)
- **Constraint:** Every model MUST use `BelongsToTenant` trait.
- **Security:** Enable Row-Level Security (RLS) at DB level.
- **Indexing:** `tenant_id` MUST be indexed on all scoped tables.

## 3. Separate Schema/DB
- **Automation:** Provisioning MUST be asynchronous (Queue).
- **Migration:** Use parallelized migration runners.
- **Cleanup:** Implement automated data purging/offboarding.

## 4. Enterprise Security
- **SSO/SAML:** Tenant-aware IdP discovery by email domain.
- **RBAC:** Roles and permissions MUST be scoped per tenant.
- **Audit:** Activity logs MUST include `tenant_id`.

## 5. Billing & Onboarding
- **Source of Truth:** External gateway (Stripe/Paddle) is the master.
- **Webhooks:** Mandatory for state synchronization.
- **TTV:** Minimize steps to first value (< 30s provisioning).
