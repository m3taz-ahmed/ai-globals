[WORKFLOW] 38-invoice-payment
[OBJ] Quote→invoice→track→reconcile flow for freelance billing using the `invoice-manager` skill and invoiceninja entity model (Client→Invoice→Payment), with multi-currency and collection follow-up.
[TRIGGER] invoice | فاتورة | payment | عرض سعر | quotation | تحصيل
[RULES]
1. [REQ] Quote: hand off to `invoice-manager` to produce a quote from the signed contract scope and agreed rate. Do not send without approval.
2. [REQ] Invoice: convert the approved quote into an invoice (multi-currency: USD/EUR/SAR/AED/EGP) with clear due date and payment methods.
3. [REQ] Track: monitor invoice status (sent/paid/overdue) and log payment events to `billing_ledger`. Surface overdue items weekly.
4. [REQ] Reconcile: match incoming payments to invoices and flag partial/unmatched amounts. Update `Memory.md` with cash position.
5. [REQ] Follow-up: draft a polite dunning reminder for overdue invoices; require approval before sending.
6. [REQ] Approval gate: no invoice send, payment record write, or reminder dispatch without explicit user approval.
[PROHIBIT]
1. No invoice send, payment record, or reminder without explicit user approval.
2. No phantom billing or amounts not backed by an approved contract.
3. No ToS violations on payment platforms.
4. Respect marketing-compliance: no payment comms to unrelated lists; GDPR for any stored payer data.
