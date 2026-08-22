[TECH] paypal
[OBJ] PayPal — Orders API v2, webhooks, subscriptions, PayPal Complete Payments, Venmo, Payouts, fraud management.
[RULES]
1. [REQ] Use the Orders API v2 (`/v2/checkout/orders`) for all one-time payments; create the order with `intent: CAPTURE`, then call `/capture` after buyer approval — never use the deprecated v1 orders or payment APIs.
2. [REQ] Authenticate via OAuth 2.0 client credentials; request access tokens with `scope=https://api.paypal.com/` and cache tokens until 80% of `expires_in` — never hardcode credentials, use environment variables or a secrets manager.
3. [REQ] Use PayPal Complete Payments SDK (`@paypal/paypal-server-sdk`) for server-side integration; create orders server-side and pass the `orderID` to the client SDK (`@paypal/react-paypal-js`) for approval — never create orders from the client.
4. [REQ] Verify webhook signatures via the `/v1/notifications/verify-webhook-signature` endpoint; check `transmission_id`, `transmission_time`, `cert_url`, `auth_algo`, and `transmission_sig` — never process webhooks without signature verification.
5. [REQ] Handle webhook events idempotently; store the `event_id` and skip duplicate deliveries — PayPal may retry failed webhook deliveries, so implement deduplication with a database unique constraint.
6. [REQ] For subscriptions, use the Subscriptions API (`/v1/billing/subscriptions`) with product and plan creation; handle `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.CANCELLED`, and `PAYMENT.SALE.COMPLETED` webhooks for lifecycle management.
7. [REQ] Enable Venmo as a payment option via the PayPal Smart Buttons with `enableFunding: ['venmo']`; Venmo flows through the same Orders API v2 — no separate integration required.
8. [REQ] Use the Payouts API (`/v1/payments/payouts`) for mass payments; create payout items with `recipient_type: EMAIL` and handle `PAYOUTS.ITEM.SUCCEEDED` and `PAYOUTS.ITEM.FAILED` webhooks — never use Payouts for customer refunds (use the Payments API `refund` endpoint).
9. [REQ] Implement fraud management via the Fraud Management Filters API (`/v1/risk/fraud-metrics`); review `ACCEPT`, `DENY`, and `REVIEW` filter results and log decisions for audit — never auto-accept high-risk transactions without review.
10. [REQ] Handle API errors by parsing the `error.response` body for `name`, `message`, `debug_id`, and `details[]`; log `debug_id` for PayPal support escalation and implement retry with exponential backoff for 5xx errors.
11. [PROHIBIT] Never store PayPal buyer credentials or credit card numbers; never process payments without capturing the order after buyer approval; never trust client-side payment confirmation without server-side order verification.
12. [PROHIBIT] Never use the PayPal sandbox credentials in production or vice versa; never skip webhook signature verification in production; never hardcode webhook listener URLs — use environment variables.
[COMPAT]
- Orders API v2 (2024): GA, PayPal Complete Payments SDK `@paypal/paypal-server-sdk` v1.x.
- Client SDK: `@paypal/react-paypal-js` v8.x, `@paypal/paypal-js` v7.x.
- Subscriptions API v1: GA, webhooks via Developer Dashboard.
[REFS]
- https://developer.paypal.com/api/rest/
- https://developer.paypal.com/docs/checkout/orders/v2/
- https://developer.paypal.com/docs/integration/direct/webhooks/
- https://developer.paypal.com/docs/subscriptions/
- https://developer.paypal.com/docs/payouts/
