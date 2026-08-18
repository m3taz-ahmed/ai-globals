# Workflow 22 — Spec Cross-Artifact Analysis

> **Trigger:** `spec-analyze`, `analyze spec`, `check spec consistency`
> **Engine:** `runtime/spec_engine.py` → `SpecEngine.analyze_artifacts()`

## Overview

Non-destructive cross-artifact consistency analysis across `spec.md`, `plan.md`, and `tasks.md`. Detects coverage gaps, duplication, ambiguity, underspecification, constitution violations, and terminology drift **before** implementation.

Inspired by GitHub Spec Kit's `analyze` command. Read-only — never modifies files.

## When to Run

- After `tasks` phase produces `tasks.md` (before `implement`)
- After any spec/plan/tasks edit to verify consistency
- Before declaring a feature ready for implementation

## Execution

```python
from pathlib import Path
from runtime.spec_engine import SpecEngine

engine = SpecEngine(Path(".ai/specs"))
report = engine.analyze_artifacts("user-auth")
print(report["metrics"])
# {
#   "total_requirements": 5, "total_tasks": 12, "coverage_pct": 80.0,
#   "ambiguity_count": 2, "unresolved_count": 0, "constitution_violations": 0
# }
for finding in report["findings"]:
    print(f"[{finding['severity']}] {finding['id']}: {finding['summary']}")
```

## Detection Categories

| Category | Severity | Description |
|----------|----------|-------------|
| `coverage_gap` | HIGH | Requirement with no associated task |
| `ambiguity` | MEDIUM | Vague term (fast/scalable/secure) without measurable criteria |
| `underspecification` | HIGH | Unresolved `[NEEDS CLARIFICATION]` or TODO/FIXME markers |
| `constitution_violation` | CRITICAL | MUST principle not reflected in spec/plan |

## Output Structure

```json
{
  "spec_id": "user-auth",
  "metrics": {
    "total_requirements": 5,
    "total_tasks": 12,
    "coverage_pct": 80.0,
    "ambiguity_count": 2,
    "unresolved_count": 0,
    "constitution_violations": 0
  },
  "findings": [...],
  "critical_count": 0,
  "high_count": 1,
  "medium_count": 2
}
```

## Next Actions

- **CRITICAL findings**: Resolve before `implement` — fix constitution or spec
- **HIGH findings**: Resolve or explicitly accept risk
- **MEDIUM/LOW**: Optional — proceed with improvement suggestions

## aiZee Gates

- Read-only: no file modifications
- Constitution MUST principles = CRITICAL (non-negotiable)
- Template-only constitutions skipped gracefully
- Max 50 findings (overflow summarized)
