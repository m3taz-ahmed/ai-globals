[TECH] stripe-integration
[OBJ] Stripe Integration (Laravel Cashier).
[RULES]
1. [REQ] Core: Cashier for subs. Stripe Checkout Sessions (PCI compliance). Customer Portal for billing UI.
2. [REQ] Advanced: Setup Intents for saving cards. Metered billing. Handle SCA / 3D Secure.
3. [REQ] Webhooks: Verify signatures via Cashier middleware. Enforce idempotency.
4. [PROHIBIT] Constraints: NEVER store raw CC/CVV. NEVER process webhooks without signature verify. ALWAYS use idempotency keys.
