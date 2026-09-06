---
name: subagent-driven-development
description: Subagent-driven development workflow.
---

[SKILL] subagent-driven-development
[OBJ] Dispatch subagents for continuous, parallel, and isolated task execution with quality gates.
[RULES]
1. [REQ] Process:
   - Read plan.
   - Dispatch `implementer` per task. Wait for TDD self-review.
   - Dispatch `spec-reviewer` to verify gaps.
   - Dispatch `code-quality-reviewer`.
   - Mark task complete. Auto-move to next task.
2. [PROHIBIT] Red Flags: No parallel implementation of dependent tasks. NEVER skip quality/spec reviews.
3. [REQ] Parallel subagent execution: dispatch independent tasks in parallel for throughput. Dependent tasks MUST be sequential — never dispatch a task whose inputs depend on an incomplete sibling.
4. [REQ] Subagent context isolation: each subagent receives only the context it needs — its task spec, relevant files, and constraints. No shared global state between subagents. Prevents context bleed and correlated failures.
5. [REQ] Subagent tool scoping: restrict each subagent's tool access to the minimum required for its task. Implementer gets edit/exec; reviewer gets read-only. No blanket tool access.
6. [REQ] Orchestrator-worker pattern: the orchestrator dispatches tasks, aggregates results, and handles failures. Workers execute single tasks and return structured results. Orchestrator never implements directly.
7. [REQ] Result aggregation: orchestrator collects subagent results, validates completeness against the plan, and merges outputs. Conflicts between subagent outputs trigger a reconciliation pass.
8. [REQ] Failure handling: on subagent failure, retry once with expanded context. On second failure, fall back to a simpler decomposition. On third failure, escalate to human with full trace.
9. [REQ] Quality gates per subagent: every subagent output passes through spec-review (does it meet the task spec?) and code-quality-review (lint, types, tests, security) before the orchestrator accepts it.
10. [REQ] Subagent memory management: subagents do not persist memory across tasks. Each dispatch is stateless. Long-term state lives in the orchestrator's `Memory.md` and `active-context.md`.
11. [REQ] Subagent cost tracking: track tokens, duration, and call count per subagent dispatch. Aggregate at the orchestrator level. Flag anomalous spend (spike or budget breach).
12. [REQ] Subagent observability: trace every subagent dispatch with OpenTelemetry spans. Record task ID, subagent role, inputs, outputs, duration, cost, and verdict (pass/fail/retry).
13. [REQ] Claude Code subagent patterns: use Explore subagent for codebase research, Plan subagent for decomposition, and custom subagents for specialized roles (implementer, reviewer, tester). Match subagent type to task complexity.
14. [REQ] Cursor agent patterns: use Composer for multi-file implementation, Plan mode for decomposition and review. Define agent boundaries explicitly — no agent should exceed its declared scope.
15. [PROHIBIT] Anti-patterns: god-orchestrator (orchestrator implements directly), tight coupling between subagents (shared mutable state), skipping reviews to save time, and dispatching dependent tasks in parallel.
