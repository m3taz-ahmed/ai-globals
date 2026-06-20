[WORKFLOW] security-standards
[OBJ] Security & Cyber Resilience.
[RULES]
1. [REQ] Data `[SEC-08]`: Encrypt DB PII. Private Cloud buckets with Signed URLs. NO secrets in logs.
2. [REQ] Input `[SEC-01]`: Strict `FormRequest`. Escape HTML. Strict JSON MIME type.
3. [REQ] DB/Auth `[SEC-02]`: Parameterized queries. Whitelist `$fillable`. Deny by default (Policies/Gates).
4. [REQ] Network: Prevent SSRF (NO local IP resolution). Verify Webhook HMAC.
5. [REQ] Uploads: Validate extension/MIME/Size. Store outside `public/`.
6. [REQ] Sessions: Throttle APIs. HttpOnly/Secure cookies. `Session::regenerate()`.
7. [REQ] AI Security: Sanitize against goal hijacking. Enforce JSON schema. UUIDv4 IDs. mTLS for M2M.
