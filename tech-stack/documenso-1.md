[TECH] documenso-1
[OBJ] Documenso — open-source document signing (AGPL-3.0, "DocuSign alternative"). Template → fields → sign → audit trail. Rules + data model for aiZee contract-studio / freelance-platforms skills.
[RULES]
1. [REQ] License: AGPL-3.0. Use as self-hosted service/plugin; do NOT vendor core code. Deploy via Docker (`documenso/documenso`) + Postgres.
2. [REQ] Data model: Document (template or raw) → Recipient(s) → Field(s) (signature/initial/date/text/checkbox, anchored) → Signature (signed payload) → AuditTrail (events + hashes).
3. [REQ] API: REST v1 + TypeScript SDK (`@documenso/sdk`). Core: `/documents` (create/send), `/templates` (create via `/templates` + `/templates/{id}/fields`), `/fields`, `/webhooks`. Auth: bearer API token from dashboard.
4. [REQ] Flow: create template → add fields per recipient (role signer/viewer/cc) → send to recipients → signers complete → document locked + tamper-evident audit log.
5. [REQ] Fields: support typed fields (signature, initial, name, email, date, text, checkbox, radio, dropdown). Anchor via pixel or template drag-drop.
6. [REQ] Arabic/RTL: upload RTL Arabic PDFs; field labels can be Arabic; signer UI supports RTL. Ensure template text uses `dir="rtl"` where rendered.
7. [REQ] Audit: every action (view, sign, complete) hashed + timestamped; downloadable certificate. Required for legal enforceability.
8. [REQ] Integration: after signing, hand off to `invoice-manager` (invoiceninja-1) for first invoice; store signed doc ref in memory.
9. [REQ] Approval gate: aiZee drafts contract, but [PROHIBIT] auto-sign. Human must sign in Documenso. See `contract-studio`.
10. [REQ] Webhooks: `document.completed`, `document.signed` → notify workflow + store in `freelance-tools`.
11. [REQ] Python SDK: community `documenso` Python client (MIT) wraps REST; prefer official TS SDK in Node plugins. Never store API token in code.
12. [PROHIBIT] ⛔ Vendor AGPL core. ⛔ Auto-sign on user's behalf. ⛔ Store tokens/PII in code/logs/commits. ⛔ Send without explicit user approval.
13. [CMD] Context7: `documenso/documenso` (fallback official docs).
14. [REQ] Free-first note: self-host = $0 software; only infra. Preferred over DocuSign/HelloSign for cost + data control.
