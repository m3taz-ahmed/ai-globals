[WORKFLOW] 43-arabic-freelance
[OBJ] RTL-aware proposal/contract/invoice flow tailored to Arabic freelance platforms (Mostaql/Khamsat/Nabbesh/Bayt) with local-currency pricing and platform-feed analysis.
[TRIGGER] mostaql | خمسات | مستقل عربي | arabic freelance | منصة عربية | nabbesh
[RULES]
1. [REQ] Locale: produce all client-facing docs RTL (Arabic) with SAR/AED/EGP pricing and Arabic contract clauses.
2. [REQ] Platform: apply per-platform rules (Mostaql/Khamsat/Bayt) for feeds, bids, and milestones.
3. [REQ] Proposal: hand off to `freelance-platforms` + `proposal-writer` for a bilingual AR/EN bid.
4. [REQ] Contract/Invoice: route signed work to `contract-studio` and `invoice-manager` with local currency.
5. [REQ] Compliance: respect each platform's ToS on communication and payment.
6. [REQ] Record: log Arabic engagements and currency in `Memory.md`.
7. [REQ] Approval gate: no bid, message, contract, or invoice without explicit user approval.
[PROHIBIT]
1. No bid, message, contract, or invoice on Arabic platforms without explicit user approval.
2. No ToS violations on Mostaql/Khamsat/Bayt/Nabbesh.
3. No off-platform payment solicitation before escrow is confirmed.
4. Respect marketing-compliance: opt-in and GDPR for any collected client contacts.
