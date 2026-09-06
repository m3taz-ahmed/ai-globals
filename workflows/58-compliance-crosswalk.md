# Workflow 58 — Compliance Crosswalk Audit

[TRIGGER] compliance crosswalk, iso 42001, nist ai rmf, eu ai act, uagt, compliance audit, تدقيق الامتثال
[PERSONA] LEGAL, SEC, ARCH, PRODUCT, DOC
[TECH] mcp-2

## Objective

Perform unified compliance audit using UAGT (Unified AI Governance Taxonomy) crosswalk — one audit, three frameworks (ISO 42001 + NIST AI RMF + EU AI Act including Digital Omnibus).

## Steps

1. **Run `aizee compliance check`.** Maps all aiZee rules to regulatory articles and reports coverage gaps. Verify output includes EU AI Act, NIST AI RMF, ISO 42001 mappings.

2. **EU AI Act Digital Omnibus check.** Verify compliance with Regulation (EU) 2026/1744 (published 24 Jul 2026, in force 27 Jul 2026):
   - Art. 5 original prohibitions (in force since 2 Feb 2025) — verify no prohibited practices. Digital Omnibus new prohibitions effective 2 Dec 2026.
   - Art. 50 transparency (in force 2 Aug 2026, NOT deferred) — verify AI content labeling, chatbot disclosure, deepfake detection metadata.
   - Annex III high-risk (deferred to 2 Dec 2027) — prepare risk management system.
   - Annex I high-risk (deferred to 2 Aug 2028) — prepare conformity assessment.
   - Penalties up to €35M or 7% of global turnover.

3. **NIST AI RMF mapping.** Verify 4 functions mapped:
   - GOVERN → `global-roles.md` + `runtime/policy.py`
   - MAP → `runtime/spec_engine.py` + `runtime/agent_catalog.py`
   - MEASURE → `eval/reliability.py` + `eval/harness.py`
   - MANAGE → `runtime/agent_gateway.py` + `runtime/guardian.py`

4. **ISO 42001 mapping.** Verify clauses mapped:
   - Clause 4 (Context) → `spec.md` + `ACTIVE_CONTEXT.md`
   - Clause 6 (Planning) → `workflows/01-planning.md`
   - Clause 8 (Operation) → `runtime/kernel.py` 5-gate pipeline
   - Clause 9 (Performance evaluation) → `eval/harness.py` + `aizee test --full`
   - Clause 10 (Improvement) → `workflows/06-maintenance.md` + `Memory.md`

5. **UAGT crosswalk.** Map aiZee rules to 8 regulation-stable governance domains (UAGT reconciles ISO 42001 + NIST AI RMF + EU AI Act). One audit, three frameworks.

6. **MITRE mapping.** Map detection rules to MITRE ATLAS v2026.06, ATT&CK v19.1, CWE 4.20, CSA AI Controls Matrix v1. Cross-reference with OWASP LLM/ASI Top 10s.

7. **Risk tier classification.** Verify every AI action classified:
   - `minimal` (code formatting) → auto-allow
   - `limited` (code generation) → allow + audit
   - `high` (deploy, DB migration) → ask + human approval
   - `unacceptable` (mass PII collection) → deny always

8. **Audit trail retention.** Verify audit logs retained per regulatory minimum (EU AI Act: 6 months post-deployment; ISO: per org policy). `runtime/audit.py` rotation respects this.

9. **Data residency.** Verify actions that move data across residency boundaries are flagged (PDPL for Saudi, GDPR for EU). Cross-boundary = WARN + LEGAL review.

10. **Right to explanation.** Verify every high-tier action produces human-readable explanation from audit trail. `audit.read_entries()` + `composite_identity.resolve()`.

11. **Model cards.** Verify every model in `runtime/agent_catalog.py` has a model card: provider, tier, training cutoff, known limitations.

12. **Incident reporting.** Verify `workflows/19-incident-response.md` includes regulatory notification timelines per EU AI Act Article 73: 15 days for ordinary serious incidents; 2 days for widespread infringement / critical infrastructure disruption; 10 days for death.

13. **Third-party AI registration.** Verify any third-party AI tool (Cursor, Claude, Copilot) used in SDLC is registered in `runtime/agent_catalog.py` with risk tier.

14. **Documentation as evidence.** Verify `Memory.md`, `CHANGELOG.md`, `spec.md` serve as compliance evidence. Stale docs = compliance gap. Reconcile any drift.

15. **Market alignment (NOT compliance).** Align governance features with Gartner Magic Quadrant for Enterprise AI Coding Agents (May 2026) [VERIFY: cite licensed copy] and Forrester Agentic Development Platforms Landscape, Q3 2026 (RES198045) [VERIFY: cite licensed copy]. 12-field audit schema for procurement. These are market intelligence targets, not legal compliance requirements.

16. **Vendor independence.** Document aiZee positioning against market consolidation (Promptfoo→OpenAI, Portkey→Palo Alto, Langfuse→ClickHouse, Helicone→Mintlify, Lakera→Check Point). Open, self-hostable governance = competitive moat.

17. **Generate compliance report.** Output:
    ```
    aizee compliance check
    → EU AI Act Digital Omnibus: Art 5 ✓, Art 50 ✓, Annex III (prep), Annex I (prep)
    → NIST AI RMF: 4/4 functions mapped
    → ISO 42001: 5/5 clauses mapped
    → UAGT: 8/8 domains mapped
    → MITRE: ATLAS v2026.06, ATT&CK v19.1, CWE 4.20, CSA AICM v1
    → Risk tiers: 4/4 defined
    → Audit retention: 6 months (EU AI Act compliant)
    → Coverage gaps: 0
    ```

18. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`, `python eval/harness.py`. Run `aizee compliance check`. Verify 0 coverage gaps.

19. **Memory sync.** Update `Memory.md` with compliance audit milestone. Update `CHANGELOG.md` `[Unreleased]` section.

## References

- `skills/compliance-lord/SKILL.md` — Compliance lord
- https://eur-lex.europa.eu/ — EU AI Act Digital Omnibus
- https://www.nist.gov/itl/ai-risk-management-framework — NIST AI RMF
- https://www.iso.org/standard/42001 — ISO 42001
- https://arxiv.org/html/2608.07515 — UAGT
