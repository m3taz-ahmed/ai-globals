#!/usr/bin/env python3
"""Task Contract — enforced decompose → execute → verify → review lifecycle.

Turns the spec-engine pipeline into an always-on contract for multi-step
work:

1. **Classify** — every work prompt is classified ``trivial | standard |
   complex`` with a recorded justification (``classifications.jsonl``).
2. **Decompose** — non-trivial work requires ``.task/plan.json``: atomic
   tasks with stable kebab ids, acyclic deps, declared scope, ``produces``
   handoff contracts, and acceptance checks.
3. **Execute** — one active task; deps must be ``done`` before starting.
4. **Verify** — ``done`` requires recorded evidence, not claims.
5. **Final review** — ``finish()`` emits the FULL-tier checklist plus
   scope/evidence gaps.

Enforcement: L1 rules (always-on) · L2 hooks (inject + observe warnings) ·
L3 ``AIZEE_TASK_STRICT=1`` (scope violations raise).
"""

from __future__ import annotations

from runtime.task_contract.classifier import classify_prompt
from runtime.task_contract.engine import TaskContractManager
from runtime.task_contract.models import (
    CLASSIFICATIONS_FILE,
    PLAN_FILE,
    REVIEW_DIR,
    STRICT_ENV,
    TASK_DIR,
    Classification,
    ContractTask,
    PlanStatus,
    Risk,
    TaskContractError,
    TaskPlan,
    TaskStatus,
)

__all__ = [
    "CLASSIFICATIONS_FILE",
    "PLAN_FILE",
    "REVIEW_DIR",
    "STRICT_ENV",
    "TASK_DIR",
    "Classification",
    "ContractTask",
    "PlanStatus",
    "Risk",
    "TaskContractError",
    "TaskContractManager",
    "TaskPlan",
    "TaskStatus",
    "classify_prompt",
]
