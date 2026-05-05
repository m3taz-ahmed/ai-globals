# Tech-Stack: SaaS Billing & Subscriptions

## Core Billing Engine
- **International:** Stripe / Paddle via Laravel Cashier.
- **Regional (MENA):** Paymob, Tap, Moyasar adapters.
- **Mode:** Subscription-first with usage metering support.

## Feature Gating
- **Laravel Pennant:** Define features based on plan tier.
- **Real-time:** Updates must reflect immediately on tier change.

## Usage Metering
- **Ingestion:** High-performance async event capture (Redis).
- **Aggregation:** Scheduled tasks to report totals to gateway.

## Compliance
- **PCI:** Never handle raw card data (use hosted checkout).
- **Invoicing:** Automated PDF generation per tenant.
