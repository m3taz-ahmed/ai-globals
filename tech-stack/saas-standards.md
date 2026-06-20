[TECH] saas-standards
[OBJ] SaaS Architectural Standards.
[RULES]
1. [REQ] Shared DB [SaaS-01]: Model MUST use `BelongsToTenant` trait. `tenant_id` indexed.
2. [REQ] Separate DB [SaaS-02]: Async provisioning. Parallel migrations. Auto purging.
3. [REQ] Security [SaaS-03]: Tenant-aware SSO. Scoped RBAC. Audit logs require `tenant_id`.
4. [REQ] Billing [SaaS-04]: External gateway is master. Webhook sync. TTV < 30s.
