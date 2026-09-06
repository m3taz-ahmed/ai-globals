# Workflow 57 — Durable Execution Setup

[TRIGGER] durable execution, temporal setup, inngest setup, dbos setup, prefect setup, restate setup, تنفيذ دائم
[PERSONA] ARCH, DEV, DEVOPS, SRE
[TECH] durable-execution

## Objective

Integrate durable execution patterns for crash-resilient, disconnect-proof AI agent workflows. Enable long-running tasks, human-in-the-loop gates, and checkpoint/replay for agent pipelines.

## Steps

1. **Select framework.** Choose based on requirements:
   - **Temporal** — workflow-as-code, durable timers, retries, signals/queries. Best for complex multi-step workflows. Self-hosted or Temporal Cloud.
   - **Inngest** — serverless durable functions, step.run/step.sleep, fan-out. Best for serverless deployments (Vercel, Cloudflare).
   - **DBOS** — Python durable workflows, transactions. Best for Python-heavy data pipelines.
   - **Prefect** — data pipelines, flow/run. Best for ML/data orchestration.
   - **Restate** — durable services, virtual objects, delayed calls. Best for microservice-style agent architectures.

2. **Identify durable candidates.** Audit agent workflows for: long-running tasks (>30s), multi-step with HITL gates, crash-sensitive pipelines, tasks needing checkpoint/replay. These are durable execution candidates.

3. **Implement idempotency.** Every durable operation must have an idempotency key. Same key + same operation = same result (no duplicate execution). Use task ID + step name as key.

4. **Checkpoint pattern.** Checkpoint after each step. On crash, resume from last checkpoint (not from start). Temporal: automatic. Inngest: step.run. DBOS: @DBOS.step. Prefect: task checkpoints. Restate: journal.

5. **Error handling.** Define retry policies: max attempts, backoff strategy, retryable vs non-retryable errors. Define compensation logic for irreversible operations (saga pattern). Define timeout per step.

6. **HITL gates.** Implement human-in-the-loop gates as durable pauses. Temporal: signals. Inngest: step.sleep until event. DBOS: checkpoint + resume. Restate: delayed calls. Agent pauses, human approves/rejects, workflow resumes.

7. **Timeout/saga pattern.** Define timeout per step. On timeout, execute compensation logic (rollback). Saga: sequence of steps with compensations. If step N fails, execute compensations for steps N-1 to 1 in reverse.

8. **Observability.** Instrument durable workflows with OpenTelemetry. Trace each step. Log checkpoints, retries, compensations. Export to Langfuse/Phoenix/LangSmith.

9. **Testing durable workflows.** Test happy path, failure path, timeout path, crash recovery path. Use framework's test utilities (Temporal: replay, Inngest: dev server, DBOS: test mode, Prefect: test mode, Restate: in-memory).

10. **Cost considerations.** Durable execution adds overhead (checkpointing, replay). Use for workflows where crash recovery is critical. For short-lived tasks (<30s, no HITL), regular async/await is sufficient.

11. **Framework selection matrix.**
    | Requirement | Recommended |
    |-------------|-------------|
    | Complex multi-step + self-hosted | Temporal |
    | Serverless (Vercel/CF) | Inngest |
    | Python data pipelines | DBOS / Prefect |
    | Microservice agents | Restate |
    | Simple HITL + retry | Inngest |
    | Enterprise + compliance | Temporal |

12. **MCP integration.** MCP tool calls within durable workflows must be idempotent. Use MCP 2026-07-28 stateless protocol (no session state). Each tool call is self-contained.

13. **Quality gate.** Run `ruff check .`, `mypy`, `aizee test --full`. Test durable workflows: happy path, failure path, timeout, crash recovery.

14. **Memory sync.** Update `Memory.md` with durable execution integration milestone. Update `CHANGELOG.md` `[Unreleased]` section.

## References

- `tech-stack/durable-execution.md` — Durable execution patterns
- `skills/durable-execution-lord/SKILL.md` — Durable execution lord
- https://temporal.io/ — Temporal
- https://www.inngest.com/ — Inngest
- https://dbos.dev/ — DBOS
- https://www.prefect.io/ — Prefect
- https://restate.dev/ — Restate
