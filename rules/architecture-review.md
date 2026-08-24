[FILE] architecture-review
[OBJ] Boundary-first architecture review method. Adapted from Hazem Ali's
enterprise-system-design principals (https://github.com/DrHazemAli/enterprise-system-design).
Applied by the ARCH persona before any consequential architecture decision.
[SOURCE] Hazem Ali, "Hazem's Principals" — engineering/ai-systems/cybersecurity disciplines.
[RULES]
1. [REQ] Ask the six questions (Object/Contract/Authority/Scope/Evidence/Recovery) in order at every boundary under review.
2. [REQ] Assign a practice level (Advisory/Assisted/Delegated/Consequential) by consequence and reversibility, not by model confidence.
3. [REQ] Make the four boundaries explicit: representation, authority, memory, consequence.
4. [REQ] Enforce the zero-trust rule: the model may propose, only an independent control plane authorizes consequence.
5. [REQ] Hold the 10 invariants (R1-R10) for the AI request lifecycle.
[METHOD]
Do not trust the visible artifact. Trust the engineered path that can prove how
an object changed representation, scope, authority, execution state, and consequence.

[QUESTIONS] The six questions — ask in order at every boundary under review:
1. [Q1] Object: What exact object exists at this boundary? (bytes, code points,
   token IDs, vectors, context, logits, decoded text, a tool proposal, committed state)
2. [Q2] Contract: Which parser, schema, tokenizer, model revision, policy, runtime,
   or protocol gives that object meaning?
3. [Q3] Authority: What can the object influence now, and did that authority
   increase at this boundary?
4. [Q4] Scope: Which user, tenant, task, environment, time window, and data
   classification constrain it?
5. [Q5] Evidence: What record proves the transformation and decision without
   retaining unnecessary sensitive content?
6. [Q6] Recovery: If the decision is wrong, how is execution stopped, contained,
   reversed, and learned from?
[RULE] A design that cannot answer one of these questions has an unspecified
boundary. An unspecified boundary is not automatically vulnerable, but its
behavior cannot yet be defended. Flag it before approval.

[TIERS] Practice levels — the model's confidence does NOT select the level.
The consequence and reversibility do.
| Advisory  | Output informs a person; no direct side effect. Evidence: input/output identity, source citations, model+prompt version. |
| Assisted  | Output proposes a bounded operation for confirmation. Evidence: Advisory + exact diff, target, policy decision, approver. |
| Delegated | Runtime executes reversible, low-impact actions. Evidence: capability scope, idempotency, limits, trace, rollback, kill switch. |
| Consequential | Runtime can affect money, access, safety, production, or regulated data. Evidence: independent verifier, human or deterministic admission, immutable audit, tested containment, named owner. |

[BOUNDARIES] Four boundaries must be explicit in any AI system design:
1. Representation boundary — bytes → normalized text → token IDs → envelope.
2. Authority boundary — retrieval candidates → promotion gate (ACL/freshness/deletion/classification).
3. Memory boundary — serving state (KV cache, scheduler queues) scoped by tenant + runtime compatibility key.
4. Consequence boundary — output admission gate before any side effect.

[INVARIANTS] Minimum invariants for AI request lifecycle (Hazem R1-R15, adapted):
- R1: No high-consequence action without an admitted output record.
- R2: Every admitted output links to one final context hash.
- R3: Every final context hash links to one promotion decision set.
- R4: Promotion decisions include tenant, subject, policy version, source lineage.
- R5: Serving-state reuse allowed only when compatibility key matches exactly.
- R6: Cache namespace always includes tenant boundary fields.
- R7: Trace spans never store secrets in attributes.
- R8: If admission fails, user-visible response carries machine-readable reason code.
- R9: If deletion status changes, future promotions from affected lineage are blocked.
- R10: If tokenizer artifact changes, cached representation identity is invalidated.

[ZERO-TRUST] Hazem's production rule: the model may propose, but only an
independent control plane may authorize consequence. A language model can
suggest a tool call, SQL query, file write, or deployment action, but the
component that decides authority MUST be separate from model generation.
Apply to every authority promotion boundary:
- Prompt → tool proposal.
- Proposal → admitted operation.
- Operation → side effect.
- Side effect → persisted state.
If a boundary increases possible consequence, it needs independent verification.

[APPLY] Use this rule in `aizee check` reviews, ARCH persona decisions, and
any `runtime/admission.py` / `runtime/guardian.py` gate evaluation.
