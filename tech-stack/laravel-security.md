[TECH] laravel-security
[OBJ] Laravel Security Hardening Standards.
[RULES]
1. [REQ] Auth: Sanctum for API tokens. Fortify/Jetstream for web. WebAuthn (`asbiin/laravel-webauthn`) for passwordless (Monica pattern). ⛔ NEVER plaintext passwords. ⛔ NEVER session-based API auth.
2. [REQ] 2FA: TOTP (`pragmarx/google2fa`) + backup/recovery codes. MFA enforcement per role (Monica/BookStack/Koel pattern). Store encrypted backup codes. ⛔ NEVER store TOTP secret unencrypted.
3. [REQ] ACL: Config-driven `config/acl.php` + route-based authorization (Bagisto/Krayin pattern). OR `filament-shield` + Spatie Permission for Filament panels. Custom permission prefixes: `getPermissionPrefixes(): array` with granular actions (publish, archive, feature, approve, schedule, manage_seo, view_analytics).
4. [REQ] Multi-Tenancy: Hierarchical (Account→Vault with VIEW/EDIT/MANAGE permissions — Monica pattern) OR Channel-based (each Channel has currency/locale/theme — Bagisto pattern). ⛔ NEVER trust tenant isolation without global scope. ⛔ NEVER expose one tenant's data to another.
5. [REQ] Content Filtering: `ezyang/htmlpurifier` or `stevebauman/purify` for user HTML. `jhfa` flags (JavaScript/HTML/Form/Allowlist — BookStack pattern). ⛔ NEVER trust user HTML. ⛔ NEVER `echo` raw content without filtering. ⛔ NEVER `{!! $userContent !!}` without purification.
6. [REQ] SVG Sanitization: `enshrined/svg-sanitize` for uploaded SVGs (Bagisto/Krayin pattern). SVGs can contain XSS scripts. ⛔ NEVER serve user-uploaded SVG without sanitization.
7. [REQ] Rate Limiting: `throttle:10,1` for sensitive endpoints (Koel pattern). Separate Redis rate limiters for AI endpoints: `RateLimiter::for('ai', ...)` `[laravel-ai]`. ⛔ NEVER expose auth/login endpoints without rate limiting.
8. [REQ] Security Headers: `SecurityHeaders` middleware for CSP, X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security (SuperDuper pattern). Register in `bootstrap/app.php` `$middleware->web(append: [SecurityHeaders::class])`.
9. [REQ] ForceHttps: `ForceHttps` middleware for production (Koel pattern). Redirect HTTP→HTTPS. Register via `$middleware->api(append: [ForceHttps::class])`.
10. [REQ] Installer Lockdown: Lock `/install` route after installation (Krayin pattern). ⛔ NEVER leave installer accessible post-install. Check `installed.lock` file or `APP_INSTALLED` env.
11. [REQ] Disposable Email Validation: `propaganistas/laravel-disposable-email` for registration (MVPable pattern). Block temp email domains. ⛔ NEVER accept disposable emails for paid/verified features.
12. [REQ] GDPR: `spatie/laravel-cookie-consent` for cookie banner (MVPable pattern). Document data processing. Provide data export/deletion endpoints.
13. [REQ] Impersonation: `lab404/laravel-impersonate` with audit log (SuperDuper/MVPable pattern). ⛔ NEVER impersonate without logging. ⛔ NEVER allow impersonation in production without explicit admin consent.
14. [REQ] UUID Primary Keys: `use HasUuids` for distributed systems (Monica/Koel pattern). ⛔ NEVER expose sequential IDs in API responses. Prevents enumeration attacks.
15. [REQ] License/Feature Gating: `RestrictPlusFeatures` middleware for feature flags (Koel pattern). `HandleDemoMode` for demo environments. Check license server via fakeable interface (`FakePlusLicenseService` in tests).
16. [REQ] FormRequest Validation `[SEC-01]`: Dedicated `FormRequest` for EVERY POST/PUT/PATCH. `rules(): array` with typed rules. `toDto(): SomeData` for DTO conversion. ⛔ NEVER `$request->all()` or inline validation in controllers.
17. [REQ] Parameterized Queries `[SEC-02]`: Eloquent / Query Builder only. ⛔ NEVER raw SQL interpolation. ⛔ NEVER `DB::raw("WHERE id = {$id}")`. Use bindings: `DB::raw('WHERE id = ?', [$id])`.
18. [REQ] `$fillable` Whitelist `[SEC-03]`: Explicit `$fillable` array on every Model. ⛔ NEVER `$guarded = []`. ⛔ NEVER mass-assign without whitelist.
19. [REQ] No PII in Logs/Commits `[SEC-04]`: ⛔ NEVER log passwords, tokens, PII. Use `Log::channel('audit')->info(...)` with redacted context. Audit log key-based redaction.
20. [REQ] RBAC Enforcement `[SEC-05]`: Policies + Gates for every resource. `Gate::authorize('vault-editor', $vaultId)`. Filament Shield for admin panels. ⛔ NEVER rely on UI hiding alone.
21. [REQ] HTML Sanitization `[SEC-06]`: DOMPurify (frontend) + HTMLPurifier (backend) for all rendered HTML. ⛔ NEVER trust Markdown/HTML output without sanitization.
22. [REQ] Explicit DTO Projections `[SEC-07]`: API Resources with explicit field selection. ⛔ NEVER `->toArray()` exposing all columns. Whitelist fields per endpoint.
23. [REQ] Encrypt at Rest `[SEC-08]`: `encrypted` cast for sensitive columns. Private signed URLs for file access. ⛔ NEVER serve private files via public disk.
24. [REQ] API Throttling `[SEC-09]`: Rate limiting on ALL API endpoints. Per-IP + per-user limits. `throttle:api` default + custom limiters for sensitive routes.
25. [REQ] JWT in HttpOnly Cookies `[SEC-10]`: Regenerate session on login. ⛔ NEVER store tokens in localStorage. ⛔ NEVER CORS wildcard `*`.
