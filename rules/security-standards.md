# Security & Cyber Resilience
> [!NOTE]
> Trigger: API design, authentication, database schema, or AI agent tasks.

## Data Protection `[SEC-08]`
- **Encryption:** Encryption at rest for sensitive DB fields.
- **Storage:** Cloud buckets PRIVATE by default. Use signed URLs.
- **Audit Trails `[OBS-04]`:** Log state-changing actions.
- **Secrets Safety `[SEC-04]`:** ⛔ log or commit PII, tokens, keys, or `.env`.

## Input & Output Validation `[SEC-01]`
- **Trust No Input:** Strict validation via `FormRequest`.
- **Sanitization `[SEC-06]`:** Escape all outputs to prevent XSS.
- **MIME:** Strict JSON response headers to prevent sniffing.

## Database & Auth Security `[SEC-02]`
- **SQLi:** Parameterized queries / Eloquent only. ⛔ raw SQL string concatenation.
- **Mass Assignment `[SEC-03]`:** Whitelist `$fillable`. ⛔ `$guarded = []`.
- **Default Deny `[SEC-05]`:** Deny by default; verify access using Policies/Gates. Filament Shield RBAC.

## Rate Limiting & Throttling `[SEC-09]`
- **Middleware:** ALL routes throttled (e.g. 60 req/min). Progressive failed auth lockout.

## Session & JWT Security `[SEC-10]`
- **Cookies:** Store JWT in HttpOnly, Secure, SameSite cookies. ⛔ localStorage.
- **Session:** Call `Session::regenerate()` after login.

## Agentic AI Security (OWASP 2026) `[SEC-11]`
- **Hijack Prevention:** Sanitize inputs to prevent goal hijacking. Enforce JSON schema validation.
- **Inter-Agent:** Scoped and mutually authenticated (mTLS/tokens) machine-to-machine APIs.
- **Identifiers:** Always use unpredictable UUIDv4 for resources. ⛔ auto-increment IDs.
