# Workflow 23 — Spec-to-Code Convergence

> **Trigger:** `spec-converge`, `converge spec`, `check spec implementation`
> **Engine:** `runtime/spec_engine.py` → `SpecEngine.converge_to_code()`

## Overview

Assess the codebase against a feature's spec/plan/tasks to identify remaining work. Classifies gaps as `missing`, `partial`, `contradicts`, or `unrequested`. Suggests remediation tasks (append-only style).

Inspired by GitHub Spec Kit's `converge` command. Read-only — does NOT modify any files or append tasks automatically. Returns a structured report for human/AI review.

## When to Run

- After `implement` phase has executed tasks
- When resuming a partially-implemented feature
- Before declaring a feature complete (final convergence check)

## Execution

```python
from pathlib import Path
from runtime.spec_engine import SpecEngine

engine = SpecEngine(Path(".ai/specs"))
report = engine.converge_to_code("user-auth", Path("."))
print(report["metrics"])
# {
#   "requirements_checked": 5, "tasks_incomplete": 2,
#   "findings_total": 3, "missing_count": 1, "partial_count": 2
# }
print(report["converged"])  # True if zero findings
for task in report["suggested_tasks"]:
    print(f"{task['id']} [{task['severity']}] {task['description']}")
```

## Gap Types

| Gap Type | Severity | Description |
|----------|----------|-------------|
| `missing` | HIGH | Required work absent from code entirely |
| `partial` | MEDIUM | Work exists but doesn't fully satisfy requirement |
| `contradicts` | CRITICAL | Code conflicts with stated intent or constitution MUST |
| `unrequested` | LOW | Code contains work not called for by spec/plan/tasks |

## Output Structure

```json
{
  "spec_id": "user-auth",
  "codebase_dir": ".",
  "files_scanned": 42,
  "metrics": {
    "requirements_checked": 5,
    "tasks_incomplete": 2,
    "findings_total": 3,
    "missing_count": 1,
    "partial_count": 2
  },
  "findings": [...],
  "suggested_tasks": [
    {"id": "T013", "description": "...", "source_ref": "REQ-003", "gap_type": "missing", "severity": "HIGH"}
  ],
  "converged": false
}
```

## Next Actions

- **`converged: true`**: Implementation satisfies spec — proceed to review/PR
- **`converged: false`**: Review `suggested_tasks`, add to spec via `engine.add_task()`, re-run `implement`

## aiZee Gates

- Read-only: no file modifications (suggested tasks returned, not appended)
- Code scan capped at 500 files for performance
- Common ignore dirs excluded (.git, __pycache__, node_modules, vendor, .venv, dist, build)
- Keyword matching heuristic — not a semantic diff tool
- Constitution violations = CRITICAL

## Limitations

- Keyword-based matching (not semantic) — may produce false positives/negatives
- Does not track git history or diffs — assesses present state only
- Suggested tasks are advisory — human/AI must review before adding
