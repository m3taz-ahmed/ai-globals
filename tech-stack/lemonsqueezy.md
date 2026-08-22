[TECH] lemonsqueezy
[OBJ] LemonSqueezy — checkout, variants, subscriptions, license keys, webhooks, tax compliance, digital products.
[RULES]
1. [REQ] Use the LemonSqueezy API (`https://api.lemonsqueezy.com/v1`) with a personal API key from the Dashboard; authenticate via `Authorization: Bearer <key>` and never expose the API key in client-side code.
2. [REQ] Create checkout links via the Checkout API (`/v1/checkouts`) with `product_id` and `variant_id`; pass `custom` object for metadata (e.g., user ID) and set `checkout_options` for discount codes and receipt links — never create checkouts from the client.
3. [REQ] Use variants to define pricing tiers (e.g., monthly, yearly, lifetime); each variant has its own `variant_id` — map variants to application plan IDs in your database for subscription tier management.
4. [REQ] For subscriptions, handle `subscription_created`, `subscription_updated`, `subscription_cancelled`, and `subscription_expired` webhooks; sync subscription status (`active`, `cancelled`, `expired`, `on_trial`) to your database on each event.
5. [REQ] Use license keys for software distribution; generate license keys via the License Keys API (`/v1/license-keys`) and validate them via the `/v1/licenses/validate` endpoint — implement activation limits and instance management via `/v1/licenses/activate` and `/v1/licenses/deactivate`.
6. [REQ] Verify webhook signatures using the `X-Signature` header (HMAC-SHA256); compute the hash of the raw request body with your webhook secret and compare in constant time — never process webhooks without signature verification.
7. [REQ] Handle webhooks idempotently; LemonSqueezy sends `meta.event_name` and a unique event ID — store processed event IDs and skip duplicates to prevent double-processing.
8. [REQ] Leverage LemonSqueezy for tax compliance (Merchant of Record); LemonSqueezy handles VAT, GST, and sales tax collection and remittance — never calculate or collect taxes yourself when using LemonSqueezy as MoR.
9. [REQ] For digital products, use the Files API to attach downloadable files to products; generate secure download URLs via the `/v1/files/generate-download-url` endpoint with expiration — never expose direct file URLs.
10. [REQ] Handle API errors by parsing the `errors[]` array in the response body; each error has `status`, `code`, `title`, `detail`, and `source.pointer` — implement retry with exponential backoff for 5xx errors and log `request_id` for support.
11. [PROHIBIT] Never store customer credit card data — LemonSqueezy is the MoR and handles PCI compliance; never bypass the LemonSqueezy checkout flow for payment processing.
12. [PROHIBIT] Never ignore webhook signature verification; never trust client-side subscription status without server-side webhook confirmation; never expose license keys in client-accessible code.
[COMPAT]
- API v1 (2024): REST JSON:API spec, webhooks via Dashboard, License Keys API GA.
- Webhooks: HMAC-SHA256 signature, `X-Signature` header.
- SDKs: No official SDK — use `fetch` or `axios` with the REST API.
[REFS]
- https://docs.lemonsqueezy.com/api
- https://docs.lemonsqueezy.com/api/checkout
- https://docs.lemonsqueezy.com/api/license-keys
- https://docs.lemonsqueezy.com/guides/webhooks
- https://docs.lemonsqueezy.com/guides/taxes
