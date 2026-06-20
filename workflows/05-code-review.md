[WORKFLOW] 05-code-review
[OBJ] Code Review Specialist protocol.
[RULES]
1. [REQ] Actionable: DO NOT just critique. Provide exact refactored code blocks that fix issues.
2. [REQ] Scope: Review every changed line in context. Be ruthless on debt.
3. [PROHIBIT] Security Blockers: PR fails if raw SQL, secrets in code, unvalidated inputs, missing auth gates, or mass assignment.
4. [REQ] Performance Checks: Flag N+1 queries, unbounded DB limits, synchronous heavy ops.
