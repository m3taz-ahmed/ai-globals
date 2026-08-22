[TECH] webhooks
[OBJ] Webhook integration standards — signature verification, retry strategies, idempotency, event ordering, dead letter queues, and debugging.
[RULES]
1. [REQ] Verify webhook signatures on every incoming request. Use HMAC-SHA256 with the provider's signing secret. Compare with constant-time comparison (`hmac.compare_digest`) to prevent timing attacks.
2. [REQ] Use the provider's SDK signature verification when available (e.g., `stripe.webhooks.constructEvent`, `svix.verify`). Never implement custom signature parsing without consulting the provider's docs.
3. [REQ] Return `200 OK` immediately after validating the webhook and enqueueing the event for processing. Never block the HTTP response on business logic execution — use a background queue (BullMQ, Celery, Sidekiq).
4. [REQ] Implement idempotency using the event ID from the webhook payload. Store processed event IDs in a deduplication table/cache. Reject duplicate event IDs with `200 OK` (not an error) to prevent provider retries.
5. [REQ] Implement exponential backoff retry strategy for outbound webhooks. Start at 1s, double each retry, cap at 24h, max 10 attempts. Use jitter (±20%) to prevent thundering herd.
6. [REQ] Use a dead letter queue (DLQ) after max retries are exhausted. Store the full payload, headers, target URL, and failure reason for replay/debugging. Alert on DLQ depth threshold.
7. [REQ] Handle event ordering by tracking event sequence numbers or timestamps. Process events sequentially per resource ID. Use a partition key (resource ID) for queue consumers to maintain ordering.
8. [REQ] Log every webhook event with: event ID, event type, provider, timestamp, processing status, and duration. Use structured logging (JSON) for searchable audit trails.
9. [REQ] Use a webhook signing payload that includes the raw body, not a parsed JSON body. Signature verification requires the exact bytes received — parsing before verification can break the signature.
10. [REQ] For outbound webhooks, sign payloads with HMAC-SHA256 using a per-recipient secret. Include a timestamp in the header to prevent replay attacks. Reject webhooks older than 5 minutes.
11. [REQ] Use a webhook debugging tool (Stripe CLI, Svix Console, webhook.site) during development. Replay events locally with `stripe listen --forward-to localhost:8000/webhooks`.
12. [REQ] Configure webhook endpoints via the provider's dashboard or API. Register only the event types you handle. Subscribe to wildcard events (`*`) only for debugging, never in production.
13. [REQ] Use `webhook_id` header (or equivalent) from the provider for tracing. Propagate it through your logging and observability stack for end-to-end correlation.
14. [PROHIBIT] Never ignore webhook verification failures. Log the failure with the request body and headers, return `400 Bad Request`, and alert the team. Unverified webhooks are a security risk.
15. [PROHIBIT] Never process webhook payloads synchronously in the HTTP handler for operations that take >200ms. Long-running processing causes timeouts and provider retries.
[COMPAT]
- Providers: Stripe, GitHub, Svix, Clerk, Vercel, Resend, Twilio, Shopify, Slack.
- Libraries: `svix` (multi-provider), `stripe` (Stripe SDK), `@octokit/webhooks` (GitHub), `convoy` (self-hosted).
- Queues: BullMQ (Node), Celery (Python), Sidekiq (Ruby), AWS SQS + Lambda (serverless).
- DLQ: AWS SQS DLQ, RabbitMQ DLX, BullMQ dead-letter, Kafka dead-letter topic.
[REFS]
- https://docs.stripe.com/webhooks
- https://docs.svix.com/receiving/verifying-payloads
- https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries
- https://www.convoy.dev/docs
- https://stripe.com/docs/webhooks/best-practices
- https://github.com/octokit/webhooks.js
