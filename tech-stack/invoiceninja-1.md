[TECH] invoiceninja-1
[OBJ] Invoice Ninja — open-source invoicing/billing (Elastic-2.0, Laravel). Client → Invoice → Payment + recurring/multi-currency. Rules + data model for aiZee invoice-manager / freelance-platforms skills.
[RULES]
1. [REQ] License: Elastic License 2.0 (business-friendly, not AGPL). Self-host via Docker (`invoiceninja/invoiceninja`) or use hosted free tier (1 client). Do NOT vendor core.
2. [REQ] Data model (canonical): Client → Invoice (line items, taxes, discounts) → Payment (partial/full, gateway) → RecurringInvoice (subscription/retainer) → Quote → Credit → Expense. Mirror in `billing_ledger.py`.
3. [REQ] API: REST v5 (`/api/v1/...`): `/clients`, `/invoices`, `/payments`, `/recurring_invoices`, `/quotes`, `/credits`, `/expenses`. Auth: company token (header `X-Api-Token`) or OAuth. SDK: `invoiceninja/invoiceninja` (PHP), community Python client.
4. [REQ] Multi-currency: set client currency (USD/EUR/SAR/AED/EGP); invoices render in client currency; FX via configured rates. Essential for Arabic/MENA freelancers.
5. [REQ] Payment drivers: pluggable `PaymentDrivers` (Stripe, PayPal, PayTabs, Tap, MyFatoorah for MENA). Configure per client; never store card data in aiZee.
6. [REQ] Recurring/retainer: model retainers as `RecurringInvoice` (monthly/quarterly) — feeds `productized-service` + `pricing-strategy`.
7. [REQ] Quotes→Invoices: create Quote, accept → convert to Invoice (no re-key). Hand off signed Quote to `contract-studio`/Documenso (documenso-1).
8. [REQ] Tax/VAT: line-level + invoice-level taxes; supports EU VAT + regional (Arabic) VAT (15% KSA, 5% UAE). Compute in `freelance-financials`.
9. [REQ] OpenAPI: full spec at `/swagger`/`/openapi`; generate typed clients. Use `StorageFactory` for token storage, never in code.
10. [REQ] Webhooks: `invoice.sent`, `payment.received`, `invoice.payment` → `invoice-tools` + memory sync.
11. [REQ] RTL Arabic invoices: set client `locale=ar` + `direction=rtl`; Invoice Ninja renders Arabic templates.
12. [PROHIBIT] ⛔ Vendor core code. ⛔ Store API token/credentials in code/logs/commits. ⛔ Mark invoice paid without real payment event. ⛔ Send invoice without user approval.
13. [CMD] Context7: `invoiceninja/invoiceninja`.
14. [REQ] Free-first note: self-host = $0; hosted free = 1 client. Preferred over QuickBooks/FreshBooks for cost + data control.
