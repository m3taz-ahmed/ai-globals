"""Multi-stage budget escalation with directive injection.

Ported from strix (usestrix/strix) ``strix/core/hooks.py``.
Provides escalating budget warnings as cost approaches the limit:
at configurable bands (70%/85%/95% by default), escalating directives
are injected into the agent's context telling it to wind down.

Also provides subagent budget reserve: subagents are force-stopped
at a configurable reserve fraction (90% by default), leaving the
remainder for the root/orchestrator agent's final report.

This module is designed to be called by ``BudgetWindowManager`` or
``BudgetManager`` when they detect budget utilization crossing
thresholds. It does not itself track spend — it computes directives
given the current spend and limit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EscalationStage(str, Enum):
    """Escalation stages as budget utilization increases."""

    NOTICE = "notice"    # First band crossed — begin planning wind-down
    URGENT = "urgent"    # Second band — prioritize wrapping up
    CRITICAL = "critical"  # Third band — stop immediately


# Default utilization bands for each stage.
# Root agent bands (slightly earlier to allow wind-down time).
DEFAULT_ROOT_BANDS: tuple[float, float, float] = (0.70, 0.85, 0.95)
# Subagent bands (slightly later — subagents finish current task).
DEFAULT_SUBAGENT_BANDS: tuple[float, float, float] = (0.75, 0.80, 0.85)

# Default reserve fraction for subagents (stop at 90% of total budget).
DEFAULT_SUBAGENT_RESERVE: float = 0.90


# Directives injected into the agent's context at each stage.
# Root agent directives — wind down the entire operation.
_ROOT_DIRECTIVES: dict[EscalationStage, str] = {
    EscalationStage.NOTICE: (
        "As the root agent, begin planning your wind-down: avoid starting "
        "large new lines of investigation, and keep your required objectives "
        "on track so you can finish before the budget limit."
    ),
    EscalationStage.URGENT: (
        "As the root agent, prioritize wrapping up now: stop opening new "
        "lines of investigation, close out only what is essential, and "
        "move toward producing your final output."
    ),
    EscalationStage.CRITICAL: (
        "As the root agent, STOP all other work and finish immediately: "
        "secure your findings and produce your final output now — anything "
        "left unfinished when the limit is hit is discarded."
    ),
}

# Subagent directives — wind down the current subtask.
_SUBAGENT_DIRECTIVES: dict[EscalationStage, str] = {
    EscalationStage.NOTICE: (
        "As a sub-agent, begin planning your wind-down: avoid starting "
        "large new subtasks, and drive any in-progress work to a result."
    ),
    EscalationStage.URGENT: (
        "As a sub-agent, prioritize wrapping up your task now: finish work "
        "that is nearly done rather than starting anything new, and prepare "
        "to hand your results back to your parent."
    ),
    EscalationStage.CRITICAL: (
        "As a sub-agent, STOP all other work and finish immediately: "
        "report your results right now and hand them back to your parent "
        "before you are cut off."
    ),
}


@dataclass(frozen=True)
class EscalationConfig:
    """Configuration for budget escalation behavior.

    ``root_bands``/``subagent_bands`` must be sorted ascending
    (NOTICE < URGENT < CRITICAL); unsorted bands raise ValueError.
    """

    root_bands: tuple[float, float, float] = DEFAULT_ROOT_BANDS
    subagent_bands: tuple[float, float, float] = DEFAULT_SUBAGENT_BANDS
    subagent_reserve: float = DEFAULT_SUBAGENT_RESERVE
    root_directives: dict[EscalationStage, str] = field(
        default_factory=lambda: dict(_ROOT_DIRECTIVES), compare=False, hash=False
    )
    subagent_directives: dict[EscalationStage, str] = field(
        default_factory=lambda: dict(_SUBAGENT_DIRECTIVES), compare=False, hash=False
    )

    def __post_init__(self) -> None:
        for name in ("root_bands", "subagent_bands"):
            bands = getattr(self, name)
            if tuple(bands) != tuple(sorted(bands)):
                raise ValueError(f"{name} must be sorted ascending, got {bands!r}")


@dataclass(frozen=True)
class EscalationDirective:
    """A directive to inject into the agent's context."""

    stage: EscalationStage
    label: str
    message: str
    utilization: float  # Current utilization (0.0-1.0)
    is_root: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "label": self.label,
            "message": self.message,
            "utilization": round(self.utilization, 4),
            "is_root": self.is_root,
        }


def _crossed_stage(
    utilization: float,
    bands: tuple[float, float, float],
) -> EscalationStage | None:
    """Return the highest stage whose band has been crossed, or ``None``."""
    crossed: EscalationStage | None = None
    for stage, band in zip(EscalationStage, bands, strict=True):
        if utilization >= band:
            crossed = stage
    return crossed


def compute_escalation(
    spend: float,
    limit: float,
    is_root: bool = True,
    config: EscalationConfig | None = None,
) -> EscalationDirective | None:
    """Compute the escalation directive for the current spend.

    Returns ``None`` if no band has been crossed (utilization below
    the first band). Returns the highest crossed stage's directive
    otherwise.
    """
    if config is None:
        config = EscalationConfig()
    if limit <= 0:
        return None
    utilization = spend / limit
    bands = config.root_bands if is_root else config.subagent_bands
    stage = _crossed_stage(utilization, bands)
    if stage is None:
        return None
    directives = config.root_directives if is_root else config.subagent_directives
    message = directives.get(stage, "")
    return EscalationDirective(
        stage=stage,
        label=stage.value.upper(),
        message=message,
        utilization=utilization,
        is_root=is_root,
    )


def should_stop_subagent(
    spend: float,
    limit: float,
    config: EscalationConfig | None = None,
) -> bool:
    """Return ``True`` if a subagent should be force-stopped (reserve reached)."""
    if config is None:
        config = EscalationConfig()
    if limit <= 0:
        return False
    return spend >= limit * config.subagent_reserve


def is_budget_exceeded(
    spend: float,
    limit: float,
) -> bool:
    """Return ``True`` if the total budget has been exceeded."""
    if limit <= 0:
        return False
    return spend >= limit


def format_directive_message(directive: EscalationDirective) -> str:
    """Format a directive as a context-injection message string."""
    pct = round(directive.utilization * 100)
    return (
        f"[{directive.label}] Budget: {pct}% utilized. "
        f"{directive.message}"
    )


def recomputed_budget_flags(
    spend: float,
    limit: float,
    config: EscalationConfig | None = None,
) -> tuple[bool, bool]:
    """Return ``(budget_stopped, reserve_stopped)`` flags for a resumed session.

    Mirrors strix's ``recomputed_budget_flags``: after a pause/resume,
    determine whether the budget is fully stopped and whether the
    subagent reserve has been reached.
    """
    if config is None:
        config = EscalationConfig()
    if limit <= 0:
        return False, False
    budget_stopped = spend >= limit
    reserve_stopped = spend >= limit * config.subagent_reserve
    return budget_stopped, reserve_stopped
