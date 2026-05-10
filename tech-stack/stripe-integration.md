# Tech-Stack: Stripe Integration

> [!NOTE]
> **TRIGGER:** LOAD ON payment processing, subscription management, billing updates.
> **SCOPE:** Stripe via Laravel 12/13 Cashier.

## 1. Core Integration
- Use Laravel Cashier to manage subscriptions and customer data.
- Utilize Stripe Checkout Sessions for initial payment collection to offload PCI compliance to Stripe.
- Use the Stripe Customer Portal for user-managed billing (updating cards, downloading invoices, canceling subscriptions).

## 2. Advanced Billing & Webhooks
- Use Setup Intents for saving cards without immediate charges.
- Implement metered billing for usage-based SaaS models, reporting usage synchronously or via queued jobs.
- Handle Webhooks rigorously: verify Stripe signatures using the Cashier middleware, ensure idempotency by checking if an event was already processed, and handle retry logic gracefully.
- Handle SCA (Strong Customer Authentication) and 3D Secure redirects correctly via Cashier's exception handling.

## 3. Operations & Compliance
- Configure Stripe Tax to calculate and collect appropriate taxes based on customer location.
- Utilize Stripe Radar for advanced fraud protection.
- Test all billing flows using the Stripe CLI to forward webhooks to the local environment.

## 4. Hard Constraints
- NEVER store raw credit card numbers or CVVs in the local database.
- NEVER process webhook events without verifying the Stripe signature.
- ALWAYS use the Stripe API's idempotency keys when creating charges or subscriptions to prevent double-billing on network failures.

---

## ✅ STRIPE INTEGRATION COMPLIANCE CHECK (Mandatory)
- [ ] **Security:** Are webhook signatures verified and are sensitive card details kept out of the local DB?
- [ ] **Reliability:** Are idempotency keys used for all mutations?
- [ ] **UX:** Is the Stripe Customer Portal utilized to reduce custom billing UI maintenance?
