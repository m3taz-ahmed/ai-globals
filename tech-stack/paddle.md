[TECH] paddle
[OBJ] Paddle Billing platform — Paddle.js, checkout, subscriptions, proration, tax handling, Paddle Billing vs Paddle Classic.
[RULES]
1. [REQ] Use Paddle Billing (not Paddle Classic) for all new integrations; Paddle Classic is deprecated — migrate existing Classic integrations to Billing via the migration tool and updated API endpoints (`https://api.paddle.com/` vs `https://vendors.paddle.com/api/2.0`).
2. [REQ] Initialize Paddle.js via `Paddle.Initialize({ token: '<client_side_token>' })` on the client; use `Paddle.Checkout.open()` with `items` array containing `priceId` — never use the legacy Paddle.js v1 `Paddle.Setup()` for Billing integrations.
3. [REQ] Create products and prices via the Paddle Dashboard or API (`/products`, `/prices`); each price has a `price_id` — pass `priceId` to checkout and map to application plan IDs in your database.
4. [REQ] For subscriptions, handle `subscription.activated`, `subscription.updated`, `subscription.canceled`, and `subscription.paused` webhooks; sync subscription status to your database and map `status` field (`active`, `canceled`, `paused`, `past_due`).
5. [REQ] Configure proration behavior via the `proration_billing_mode` setting on subscription updates; when upgrading/downgrading plans, use `proration_billing_mode: prorated` (default) or `immediately` — never change plans without understanding proration charges.
6. [REQ] Leverage Paddle as Merchant of Record for tax compliance; Paddle handles VAT, GST, and sales tax calculation, collection, and remittance globally — never calculate taxes yourself when using Paddle as MoR.
7. [REQ] Verify webhook signatures using the Paddle signature header; decode the `paddle_signature` header (HMAC-SHA256) and compare the hash of the raw request body with your webhook secret — never process webhooks without verification.
8. [REQ] Handle webhooks idempotently; Paddle sends an `event_id` in the webhook payload — store processed event IDs and skip duplicates to prevent double-processing of subscription events.
9. [REQ] Use the Paddle API (`https://api.paddle.com/`) with API key authentication (`Authorization: Bearer <api_key>`); create transactions via `/transactions` and finalize them after checkout — never expose the API key in client-side code.
10. [REQ] Handle API errors by parsing the `error` object in the response body; each error has `code`, `detail`, and `type` — implement retry with exponential backoff for 5xx errors and log the `request_id` header for support escalation.
11. [PROHIBIT] Never store customer credit card data — Paddle is the MoR and handles PCI compliance; never bypass Paddle checkout for direct payment processing; never use Paddle Classic API endpoints for Billing integrations.
12. [PROHIBIT] Never skip webhook signature verification in production; never trust client-side checkout completion without server-side webhook confirmation; never expose API keys in frontend code or public repositories.
[COMPAT]
- Paddle Billing (2024): GA, REST API at `https://api.paddle.com/`, Paddle.js v2.
- Paddle Classic: Deprecated — migration to Billing required.
- Webhooks: HMAC-SHA256 signature, `paddle_signature` header.
[REFS]
- https://developer.paddle.com/
- https://developer.paddle.com/api-reference/
- https://developer.paddle.com/handbook/webhooks
- https://www.paddle.com/docs/billing-vs-classic
- https://developer.paddle.com/paddlejs
