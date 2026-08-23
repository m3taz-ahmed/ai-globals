"""Spec-driven development package (models, engine, scaffolding, analysis)."""

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
