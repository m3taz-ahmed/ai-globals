# Tech-Stack: SaaS Billing & Subscriptions

> [!NOTE]
> **TRIGGER:** LOAD ON BILLING, SUBSCRIPTION, OR PAYMENT-RELATED TASKS.
> **SCOPE:** STRIPE, PADDLE, MENA GATEWAYS, AND USAGE METERING.

## 1. Core Billing Engine
- **International:** Stripe / Paddle via Laravel Cashier.
- **Regional (MENA):** Paymob, Tap, Moyasar adapters.
- **Mode:** Subscription-first with usage metering support.
- **Webhooks:** Mandatory for payment state synchronization. Use `Cashier::handleWebhook()` with signature verification. Never trust client-side payment confirmations.

## 2. Subscription Lifecycle
- **Creation:** Use Cashier's `$user->newSubscription('default', $planId)->create($paymentMethod)`.
- **Upgrades/Downgrades:** Apply proration by default. Use `swapAndInvoice()` for immediate invoicing on plan changes.
- **Cancellations:** Distinguish between `cancel()` (end of period) and `cancelNow()` (immediate). Store cancellation reason for analytics.
- **Grace Period:** Use `onGracePeriod()` checks before revoking access. Never hard-cut a subscribed user.
- **Trials:** Use `trialDays()` in subscription creation. Enforce trial limits in middleware.

## 3. Feature Gating
- **Laravel Pennant:** Define features based on plan tier.
- **Real-time:** Updates must reflect immediately on tier change.
- **Pattern:** Use `Feature::active('api-access')` in middleware, not in controllers. Centralize feature definitions in a `FeatureServiceProvider`.

## 4. Usage Metering
- **Ingestion:** High-performance async event capture (Redis sorted sets or streams).
- **Aggregation:** Scheduled tasks to report totals to billing gateway.
- **Reporting:** Expose usage dashboards per tenant via Filament widget or API endpoint.
- **Overage Handling:** Define overage policies (hard cutoff vs. soft limit with alerts). Never silently charge overage without user consent.

## 5. Invoice & Receipt Management
- **Auto-generation:** PDF generation per tenant on payment success event.
- **Storage:** Store invoices in tenant-isolated storage (`Storage::disk('tenant')`).
- **Access:** Provide download endpoint with tenant ownership validation.
- **Tax Compliance:** Support multi-jurisdiction tax calculation (Stripe Tax or local VAT handlers for MENA).

## 6. Compliance & Security
- **PCI DSS:** Never handle raw card data. Use hosted checkout (Stripe Checkout) or Elements (Stripe.js).
- **Idempotency:** Use idempotency keys for all payment requests to prevent double-charging.
- **Audit Trail:** Log all billing state changes (created, paid, failed, refunded) with tenant_id and user_id.
- **Refunds:** Always process refunds through the gateway, never via direct database manipulation.

---

## ✅ BILLING COMPLIANCE CHECK (Mandatory)
- [ ] **Webhooks:** Are payment webhooks verified and idempotent?
- [ ] **Feature Gates:** Is every premium feature gated via Pennant?
- [ ] **PCI:** Is raw card data NEVER handled server-side?
- [ ] **Tenant Isolation:** Are billing records scoped to the correct tenant?
- [ ] **Refunds:** Are refunds processed through the gateway, not direct DB changes?
