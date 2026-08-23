#!/usr/bin/env python3
"""Spec-driven development engine for aiZee.

This module is a backward-compatible facade. The implementation lives in
the :mod:`runtime.spec` package:

- :mod:`runtime.spec.models` — phases, specs, deltas, manifests
- :mod:`runtime.spec.engine` — CRUD, phase gates, deltas (``SpecEngine``)
- :mod:`runtime.spec.scaffold` — template scaffolding + checklist validation
- :mod:`runtime.spec.analysis` — analyze/converge read-only reports

Implements a structured 4-phase development process:
1. **Specify** - Define what to build (user stories, requirements)
2. **Plan** - Technical design (architecture, stack, constraints)
3. **Tasks** - Break down into actionable tasks
4. **Implement** - Execute tasks with validation checkpoints

Usage::

    from runtime.spec_engine import SpecEngine
    engine = SpecEngine(Path(".ai/specs"))
"""

from __future__ import annotations

from runtime.spec.analysis import AnalysisMixin
from runtime.spec.engine import SpecEngine
from runtime.spec.models import (
    PHASE_ORDER,
    DeltaType,
    Requirement,
    Spec,
    SpecDelta,
    SpecManifest,
    SpecPhase,
    Task,
)
from runtime.spec.scaffold import ScaffoldingMixin

__all__ = [
    "PHASE_ORDER",
    "AnalysisMixin",
    "DeltaType",
    "Requirement",
    "ScaffoldingMixin",
    "Spec",
    "SpecDelta",
    "SpecEngine",
    "SpecManifest",
    "SpecPhase",
    "Task",
]


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    engine = SpecEngine(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".ai/specs"))
    print(json.dumps(engine.list_specs(), indent=2))
