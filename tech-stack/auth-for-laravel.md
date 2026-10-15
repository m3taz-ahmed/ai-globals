[TECH] auth-for-laravel
[OBJ] Headless multi-guard authentication for Laravel APIs (roundly-consulting/auth-for-laravel, MIT). PHP 8.4 / Laravel 12+.
[RULES]
1. [REQ] Install: `composer require roundly/auth-for-laravel` then `php artisan authentication:install`. Verify with `php artisan authentication:check` — NEVER declare done before the checker passes.
2. [REQ] Drivers per guard: `password`, `magic-link`, `otp` (email code), `passkey` (WebAuthn). Configure in `config/authentication.php` `guards.*.driver`. Multi-guard = separate guards per audience (users vs admins vs API clients), NOT one guard with roles.
3. [REQ] Tokens: RS256 JWT access + rotating refresh sessions. NEVER reuse a refresh token — package detects replay and revokes the session chain. Store access token memory-side; refresh via package endpoint only.
4. [REQ] 2FA: challenge engine (TOTP/email) gates the login pipeline — a 2FA-enabled account returns a challenge token, NOT an access token. Complete the challenge before issuing credentials.
5. [REQ] Invitations & verification: use package flows (`invitations`, `email-verification`) — do NOT hand-roll token tables.
6. [REQ] Activity logging: package emits auth events — pipe into the app `ActivityLogger`; assert `login`, `failed_login`, `password_reset` in tests.
7. [REQ] Architecture alignment: wrap package calls in `app/Actions/Auth/<Verb>.php` (laravel-12 §10); expose through FormRequest-validated controllers; DTO responses via `$casts`/Resources.
8. [PROHIBIT] Hard Constraints: NEVER put access/refresh tokens in URLs or logs. NEVER skip `authentication:check` post-install. NEVER disable refresh rotation. NEVER expose sequential user IDs in auth responses (HasUuids per laravel-12 §9).
