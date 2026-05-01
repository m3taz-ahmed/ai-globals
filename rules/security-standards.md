# Security & Cyber Resilience (OWASP Top 10)
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
- **Mass Assignment:** Strictly protect Models by defining `$fillable` or carefully using `$guarded`.

## 4. AUTHORIZATION
- **Default Deny:** Access should be denied by default. Explicitly grant permissions using Laravel Policies or Gates.
- **Filament Security:** Secure resources by strictly defining `canViewAny()`, `canEdit()`, and `canDelete()` based on role-based access control (RBAC).