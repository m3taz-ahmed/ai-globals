[WORKFLOW] 10-saga-reconciliation
[OBJ] Multi-Agent State Resilience and Conflict Resolution.
[RULES]
1. [REQ] Metadata: Every subagent carries `X-Saga-ID`, `X-Parent-Span`, `X-Agent-Persona`.
2. [REQ] Registration: Parent registers Saga ID and defines exact boundary for each subagent.
3. [REQ] Execution: Subagents execute strictly within sandbox.
4. [REQ] Reconciliation Handshake: Parent runs State Schema check, Diff Scan, and Conflict Scan.
5. [REQ] Resolution Matrix: Reject secondary diffs, parent merges configs, halt on architectural contradictions.
6. [REQ] Commits: Commit with Saga ID on success, rollback on failure.
