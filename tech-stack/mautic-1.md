[TECH] mautic-1
[OBJ] Open-source marketing automation platform (GPL). Email campaigns, lead scoring, drip sequences, and contact segmentation. Self-host free.
[DATA]
- License: GPL-3.0 (OSS, self-host free)
- Language: PHP 8.2+ / Symfony
- Storage: MySQL/MariaDB
- Auth: OAuth2 or API token (Basic auth header)
- Plugins: Email (SendGrid, Mailgun, Amazon SES), SMS (Twilio), Social monitoring
[API]
- REST: `/api/contacts` (CRUD), `/api/campaigns` (list/add/remove), `/api/emails` (send/track), `/api/segments` (add/remove contact)
- Auth: `Authorization: Bearer <token>` or HTTP Basic
- Rate limit: 300 req/10min (default, configurable)
- Webhook: Contact events (created, updated, deleted), campaign events
[CTX] websites/mautic_mautic
[RTL] Mautic supports RTL via template override; email templates accept Arabic UTF-8. Contact fields support bidirectional text.
[PROHIBIT]
1. No storing API tokens in frontend code — use server-side vault.
2. No sending campaigns without double opt-in (GDPR compliance).
3. No exposing Mautic API without rate limiting and auth.
