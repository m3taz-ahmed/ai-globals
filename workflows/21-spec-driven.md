# Workflow 21 — Spec-Driven Development

> **Trigger:** `spec-driven`, `spec`, `new feature with spec`
> **Engine:** `runtime/spec_engine.py`

## Overview

Structured 4-phase development process: **Specify → Plan → Tasks → Implement**.

Each phase produces a Markdown artifact and has a validation gate — you don't advance until the current phase passes its checks.

## Phases

### 1. Specify
- Define what to build (requirements, user stories)
- Use `engine.add_requirement(spec_id, description, priority, user_story)`
- **Gate:** At least 1 requirement must exist to advance

### 2. Plan
- Technical design (architecture, stack, constraints)
- Use `engine.set_plan(spec_id, plan_dict)`
- **Gate:** Plan must be non-empty to advance

### 3. Tasks
- Break down into actionable tasks with dependencies
- Use `engine.add_task(spec_id, description, depends_on, estimate_hours)`
- **Gate:** At least 1 task must exist to advance

### 4. Implement
- Execute tasks with validation checkpoints
- Use `engine.update_task_status(spec_id, task_id, status)`
- **Gate:** All tasks must be `done` to advance to `DONE`

## Usage

```python
from runtime.spec_engine import SpecEngine

engine = SpecEngine(Path(".ai/specs"))
engine.init_spec("user-auth", "User authentication feature")
engine.add_requirement("user-auth", "Users can log in with email")
engine.advance("user-auth")  # → Plan
engine.set_plan("user-auth", {"stack": "FastAPI", "db": "PostgreSQL"})
engine.advance("user-auth")  # → Tasks
engine.add_task("user-auth", "Create User model", estimate_hours=2.0)
engine.advance("user-auth")  # → Implement
engine.update_task_status("user-auth", "TASK-001", "done")
engine.advance("user-auth")  # → Done
```

## Artifacts

Each spec produces:
- `{spec_id}.json` — Machine-readable state
- `{spec_id}.md` — Human-readable Markdown artifact
