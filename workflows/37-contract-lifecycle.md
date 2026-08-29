[WORKFLOW] 37-contract-lifecycle
[OBJ] Generate→review→sign→store lifecycle for freelance contracts (NDA/SOW/MSA/IP-transfer) using the `contract-studio` skill and documenso patterns, with mandatory human legal review at every stage.
[TRIGGER] contract | عقد | NDA | SOW | اتفاقية | IP transfer
[RULES]
1. [REQ] Select: determine contract type (NDA/SOW/MSA/IP-transfer) from the engagement scope and the client's jurisdiction.
2. [REQ] Generate: hand off to `contract-studio` to assemble a bilingual (AR/EN) RTL-aware template from reusable clauses. Flag any missing clause.
3. [REQ] Review: require an explicit human legal review note for every clause. Do not auto-finalize.
4. [REQ] Sign: route to documenso (template→fields→sign→audit). Wait for the user's explicit approval before dispatching signature requests.
5. [REQ] Store: archive the signed PDF + audit trail in the storage backend via `StorageFactory`. Record contract ID and parties in `Memory.md`.
6. [REQ] Renewal: track expiry/milestone dates and surface a renewal reminder before lapse.
7. [REQ] Approval gate: no signature request, dispatch, or storage write without an explicit `yes`.
[PROHIBIT]
1. No contract generation dispatch, signature request, or storage write without explicit user approval.
2. No auto-signing or auto-finalizing of any legal document.
3. No ToS violations on signing platforms.
4. Respect marketing-compliance: never embed tracking or share contract data without consent (GDPR).
