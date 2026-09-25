[WORKFLOW] 61-task-contract
[OBJ] Forced task decomposition with per-task verification and a final review gate — the aiZee "Task Contract". State lives in `<project>/.task/` (EXE-PERSIST-01); engine is `runtime/task_contract/`.
[TRIGGER] task contract, split into tasks, decompose work, task plan, forced decomposition, قسم الشغل, تاسكات, خطة عمل, راجع كل تاسك
[RULES]

## 0. When this applies

Every prompt carrying work is classified before action:

| Class | Meaning | Contract |
|---|---|---|
| `trivial` | typo, rename, comment, single localized fix | no plan — but the classification IS recorded |
| `standard` | one capability, a few files | plan required |
| `complex` | multi-module, risk domains (auth/db/payments/deploy), enumerated asks | plan required + consider `spec` engine first |

```bash
aizee task classify --prompt "<the user request>"                    # heuristic hint
aizee task classify --prompt "..." --level standard --reason "..."   # record the call
```

A `trivial` call without a reason is rejected — *the AI must explain first*.
Heuristic/agent disagreement is flagged in `.task/classifications.jsonl`.

## 1. Decompose

```bash
aizee task decompose --title "<name>" --classification standard \
  --reason "..." --prompt "<original request>" --tasks @plan.json
```

Task schema (`--tasks` accepts a JSON list, `@file`, or `-` stdin):

```json
[
  {
    "id": "kebab-id", "title": "short name",
    "description": "what done means",
    "depends_on": ["earlier-id"],
    "files": ["src/scope/"],
    "produces": "src/api/x.py — the handoff contract for dependents",
    "acceptance": ["pytest tests/test_x.py passes", "no new mypy errors"],
    "verify_cmd": "python -m pytest tests/test_x.py -q",
    "risk": "low|medium|high"
  }
]
```

Validation rejects: duplicate/non-kebab ids, unknown deps, cycles, empty
acceptance, a second active plan.

## 2. Execute — one task at a time

```bash
aizee task status            # progress + next unblocked task
aizee task start <id>        # requires deps done; one active max
# ... do the work, inside the declared `files` scope ...
aizee task verify <id> --evidence "<test output / diff summary>" [--run]
aizee task complete <id> --note "review note"
```

- `verify --run` executes the task's `verify_cmd` (shell=False, 120s) — exit≠0 keeps it unverified.
- Every verification writes `.task/reviews/<id>.md` — review leaves artifacts.
- Stuck? `aizee task block <id> --reason "..."`.

## 3. Scope enforcement

- Edits outside the active task's `files` → warning via the `afterFileEdit` hook; `aizee task scope <path>` checks manually.
- `AIZEE_TASK_STRICT=1` turns warnings into `SCOPE_VIOLATION` errors.
- Wrong scope ≠ failure — amend the plan: `aizee task amend --ops '[{"op":"update","id":"t","task":{"files":[...]}}]' --reason "..."` (ops: `add`/`update`/`remove`).

## 4. Final review — plan closed ≠ done

```bash
aizee task finish --note "..."
```

Requires every task `done` or `blocked`. Emits `.task/reviews/<plan>-final.json`:

- `scope_gaps`: done tasks that never declared files
- `evidence_gaps`: done tasks without evidence
- `final_checklist`: FULL test tier, diff⊆scope review, acceptance conformance, lint/typecheck, cleanup gate

The work is done when the checklist passes, not when the plan closes.

## 5. Escape hatches

- `aizee task abandon --reason "..."` — kill a wrong plan, then re-decompose.
- Trivial work skips the plan — but never skips the recorded classification.
