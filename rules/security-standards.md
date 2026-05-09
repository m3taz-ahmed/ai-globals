# Security & Cyber Resilience (OWASP Top 10)
> [!NOTE]
> **TRIGGER:** LOAD ON API DESIGN, AUTHENTICATION, OR DATABASE SCHEMA TASKS.
> **SCOPE:** PRODUCTION-GRADE SECURITY STANDARDS.

- **Mindset:** Implement "Zero-Trust" architecture. Never assume an internal request is safe.

## 1. DATA PROTECTION
- **Encryption at Rest:** Sensitive database fields MUST be encrypted using Laravel's encryption or database-level encryption.
- **Environment Safety:** Never log `.env` variables or raw request bodies containing sensitive credentials/keys.
- **Audit Trails:** Every state-changing action (Create, Update, Delete) MUST be logged in an audit trail with UserID, Timestamp, and Old/New values.

## 2. INPUT & OUTPUT
- **Trust No Input:** All user inputs must be validated strictly using Laravel FormRequests.
- **Sanitization:** Prevent XSS by ensuring all user-generated content is escaped.
- **Output Encoding:** Ensure all API responses use strict JSON headers and appropriate status codes to prevent MIME-sniffing attacks.

## 3. DATABASE SECURITY
- **SQL Injection:** Never use raw string concatenation in queries. Always use Eloquent, Query Builder, or PDO Parameterized Queries.
- **Mass Assignment:** Strictly protect Models by defining `$fillable` explicitly. NEVER use `$guarded = []` (see `anti-patterns.md` §1).

## 4. AUTHORIZATION
- **Default Deny:** Access should be denied by default. Explicitly grant permissions using Laravel Policies or Gates.
- **Filament Security:** Secure resources by strictly defining `canViewAny()`, `canEdit()`, and `canDelete()` based on role-based access control (RBAC).

## 5. RATE LIMITING & DDoS MITIGATION
- **API Throttling:** ALL API routes MUST use Laravel's `ThrottleRequests` middleware. Default: 60 requests/minute per user.
- **Abuse Detection:** Implement progressive lockout (exponential backoff) for failed auth attempts.
- **Resource Limits:** Set maximum request body sizes and upload limits to prevent resource exhaustion.

## 6. JWT & SESSION SECURITY
- **JWT Storage:** Never store JWTs in `localStorage`. Use `HttpOnly`, `Secure` cookies.
- **Revocation:** Implement a blacklist or JTI-based revocation for JWTs.
- **Session Regeneration:** Call `Session::regenerate()` after every login to prevent session fixation.

## 7. CLOUD & INFRASTRUCTURE SECURITY
- **Storage Privacy:** Ensure all cloud storage buckets (S3/Azure) are PRIVATE by default. Use Signed URLs for temporary access.
- **Identity & Access (IAM):** Use "Least Privilege" IAM roles for app servers. Never use root account credentials.
- **Dependency Audits:** Run `composer audit` and `npm audit` in CI/CD. Fail on HIGH/CRITICAL issues.

---

## 8. DEPENDENCY EVOLUTION & AUDIT GATES
- **Audit-Driven Upgrades:** Avoid hard-pinning core frameworks to allow for security patches. However, moving to a new **MAJOR** version (e.g., Laravel 11→12, Tailwind 3→4) requires a mandatory "Breaking Change Impact Analysis".
- **Verified Window:** Prioritize versions within the "LTS" or "Stable" window.
- **Speculative Tech:** Rules for tech marked `[!SPECULATIVE]` must only be applied to research branches or explicitly approved experimental projects. Never merge speculative standards into the `main` production branch.
- **Transitive Security:** Before adding a new package, analyze its dependency tree for "Phantom Maintenance" (deep dependencies that are unmaintained).

---

## 🕵️ SECURITY VERIFICATION (Mandatory)
- [ ] **Validation:** Is every input passing through a strict `FormRequest`?
- [ ] **Exposure:** Are any sensitive keys or PII being logged/exposed in the API?
- [ ] **Permissions:** Is the default behavior "Deny All" for this new route?
- [ ] **SQLi:** Have I verified that no raw strings are being passed to database queries?
- [ ] **Upgrade Audit:** If a dependency was upgraded, have I reviewed the breaking changes?