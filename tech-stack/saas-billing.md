[TECH] saas-billing
[OBJ] SaaS Billing & Subscriptions.
[RULES]
1. [REQ] Engine: Stripe/Paddle (Laravel Cashier). Paymob/Tap/Moyasar (MENA).
2. [REQ] Webhooks: Mandatory for sync. Verify signature. ⛔ NEVER trust client-side payment confirmations.
3. [REQ] Subscription: `swapAndInvoice()` for upgrades. `onGracePeriod()` checks.
4. [REQ] Gating: Laravel Pennant `Feature::active()`.
5. [REQ] Usage/Overage: Async ingestion (Redis). Define policies. ⛔ NO silent overage charging.
6. [PROHIBIT] Security: PCI DSS (NO raw card data). Idempotency keys. Refunds ONLY via gateway.
