#!/usr/bin/env python3
"""Cost-aware model routing (inspired by tag).

Routes to the cheapest capable model with timeout-aware escalation.
Local models first when healthy, then cheapest tier that meets
capability requirements, respecting max_cost constraints.

Usage::

    from runtime.model_router import ModelRouter
    router = ModelRouter()
    decision = router.route("code_generation", requires_vision=False)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

_logger = logging.getLogger(__name__)


class ModelCapability(str, Enum):
    """Capabilities a model can have."""

    TEXT = "text"
    VISION = "vision"
    CODE = "code"
    REASONING = "reasoning"
    EMBEDDING = "embedding"


class RouteTier(str, Enum):
    """Cost tiers from cheapest to most expensive."""

    LOCAL = "local"
    CHEAP = "cheap"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass
class ModelInfo:
    """Information about a single model."""

    name: str
    provider: str
    tier: RouteTier
    capabilities: set[ModelCapability] = field(default_factory=set)
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    max_context: int = 4096
    supports_session: bool = False
    supports_vision: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "provider": self.provider,
            "tier": self.tier.value,
            "capabilities": [c.value for c in self.capabilities],
            "cost_per_1m_input": self.cost_per_1m_input,
            "cost_per_1m_output": self.cost_per_1m_output,
            "max_context": self.max_context,
            "supports_session": self.supports_session,
            "supports_vision": self.supports_vision,
        }


@dataclass
class RouteDecision:
    """Result of a routing decision."""

    model: str
    tier: RouteTier
    reason: str
    fallback: str | None = None
    estimated_cost: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "tier": self.tier.value,
            "reason": self.reason,
            "fallback": self.fallback,
            "estimated_cost": self.estimated_cost,
        }


# -- Built-in model catalog -------------------------------------------------
_MODELS: list[ModelInfo] = [
    # Local (free)
    ModelInfo("llama-3.1-8b", "local", RouteTier.LOCAL,
              {ModelCapability.TEXT, ModelCapability.CODE}, 0.0, 0.0, 128000, True, False),
    ModelInfo("qwen2.5-7b", "local", RouteTier.LOCAL,
              {ModelCapability.TEXT, ModelCapability.CODE}, 0.0, 0.0, 32768, True, False),
    ModelInfo("mistral-7b", "local", RouteTier.LOCAL,
              {ModelCapability.TEXT}, 0.0, 0.0, 32768, True, False),
    ModelInfo("phi-3-mini", "local", RouteTier.LOCAL,
              {ModelCapability.TEXT}, 0.0, 0.0, 4096, True, False),
    # Cheap
    ModelInfo("gpt-4o-mini", "openai", RouteTier.CHEAP,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE},
              0.15, 0.60, 128000, True, True),
    ModelInfo("claude-3-haiku", "anthropic", RouteTier.CHEAP,
              {ModelCapability.TEXT, ModelCapability.VISION},
              0.25, 1.25, 200000, True, True),
    ModelInfo("gemini-1.5-flash", "google", RouteTier.CHEAP,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE},
              0.075, 0.30, 1000000, True, True),
    ModelInfo("llama-3.1-70b", "meta", RouteTier.CHEAP,
              {ModelCapability.TEXT, ModelCapability.CODE},
              0.59, 0.79, 128000, True, False),
    # Standard
    ModelInfo("gpt-4o", "openai", RouteTier.STANDARD,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING},
              2.50, 10.00, 128000, True, True),
    ModelInfo("claude-3.5-sonnet", "anthropic", RouteTier.STANDARD,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING},
              3.00, 15.00, 200000, True, True),
    ModelInfo("gemini-1.5-pro", "google", RouteTier.STANDARD,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING},
              1.25, 5.00, 2000000, True, True),
    ModelInfo("mistral-large", "mistral", RouteTier.STANDARD,
              {ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING},
              2.00, 6.00, 128000, True, False),
    # Premium
    ModelInfo("o1", "openai", RouteTier.PREMIUM,
              {ModelCapability.TEXT, ModelCapability.CODE, ModelCapability.REASONING},
              15.00, 60.00, 200000, True, False),
    ModelInfo("o1-preview", "openai", RouteTier.PREMIUM,
              {ModelCapability.TEXT, ModelCapability.REASONING},
              15.00, 60.00, 128000, True, False),
    ModelInfo("claude-3-opus", "anthropic", RouteTier.PREMIUM,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING},
              15.00, 75.00, 200000, True, True),
    ModelInfo("gpt-4-turbo", "openai", RouteTier.PREMIUM,
              {ModelCapability.TEXT, ModelCapability.VISION, ModelCapability.CODE, ModelCapability.REASONING},
              10.00, 30.00, 128000, True, True),
]


class ModelRouter:
    """Cost-aware model router.

    Routes to the cheapest capable model with timeout-aware escalation.
    Local models are preferred when healthy, then cheapest tier that
    meets capability requirements.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._models: list[ModelInfo] = list(_MODELS)
        self._local_healthy = True
        if config_path and config_path.exists():
            self._load_config(config_path)

    def _load_config(self, path: Path) -> None:
        """Load routing configuration from JSON."""
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._local_healthy = data.get("local_healthy", True)
        except (json.JSONDecodeError, OSError) as exc:
            _logger.warning("Failed to load routing config: %s", exc)

    def route(
        self,
        task_type: str,
        requires_vision: bool = False,
        requires_session: bool = False,
        max_cost: float | None = None,
    ) -> RouteDecision:
        """Route a task to the cheapest capable model.

        Args:
            task_type: Type of task (text, code, reasoning, etc.).
            requires_vision: Whether the task needs vision capability.
            requires_session: Whether multi-turn session is needed.
            max_cost: Maximum cost per 1M tokens (input+output).
        """
        required_caps = self._task_capabilities(task_type)
        if requires_vision:
            required_caps.add(ModelCapability.VISION)
        # Try local first if healthy
        if self._local_healthy:
            local = self._find_cheapest(RouteTier.LOCAL, required_caps, requires_session, max_cost)
            if local:
                return RouteDecision(
                    model=local.name,
                    tier=RouteTier.LOCAL,
                    reason="Local model healthy and capable",
                    fallback=self._next_tier_model(local, required_caps, requires_session, max_cost),
                    estimated_cost=0.0,
                )
        # Escalate through tiers
        for tier in [RouteTier.CHEAP, RouteTier.STANDARD, RouteTier.PREMIUM]:
            model = self._find_cheapest(tier, required_caps, requires_session, max_cost)
            if model:
                return RouteDecision(
                    model=model.name,
                    tier=tier,
                    reason=f"Cheapest capable model in {tier.value} tier",
                    fallback=self._next_tier_model(model, required_caps, requires_session, max_cost),
                    estimated_cost=model.cost_per_1m_input + model.cost_per_1m_output,
                )
        # Fallback: return cheapest available regardless of constraints
        cheapest = min(self._models, key=lambda m: m.cost_per_1m_input + m.cost_per_1m_output)
        return RouteDecision(
            model=cheapest.name,
            tier=cheapest.tier,
            reason="No model meets all constraints — using cheapest available",
            estimated_cost=cheapest.cost_per_1m_input + cheapest.cost_per_1m_output,
        )

    def escalate(self, current_model: str, reason: str) -> RouteDecision:
        """Escalate from current model to the next tier up."""
        model = self.get_model(current_model)
        if model is None:
            return RouteDecision(
                model=current_model, tier=RouteTier.STANDARD,
                reason=f"Unknown model '{current_model}', keeping as-is",
            )
        tier_order = [RouteTier.LOCAL, RouteTier.CHEAP, RouteTier.STANDARD, RouteTier.PREMIUM]
        current_idx = tier_order.index(model.tier)
        if current_idx >= len(tier_order) - 1:
            return RouteDecision(
                model=current_model, tier=model.tier,
                reason=f"Already at highest tier ({model.tier.value}), cannot escalate",
            )
        next_tier = tier_order[current_idx + 1]
        next_model = self._find_cheapest(next_tier, model.capabilities, model.supports_session, None)
        if next_model is None:
            return RouteDecision(
                model=current_model, tier=model.tier,
                reason=f"No capable model in {next_tier.value} tier",
            )
        return RouteDecision(
            model=next_model.name,
            tier=next_tier,
            reason=f"Escalated from {current_model}: {reason}",
            fallback=current_model,
            estimated_cost=next_model.cost_per_1m_input + next_model.cost_per_1m_output,
        )

    def compare(self, task_type: str) -> list[dict[str, Any]]:
        """List all viable models sorted by cost."""
        required_caps = self._task_capabilities(task_type)
        viable = [
            m for m in self._models
            if required_caps.issubset(m.capabilities)
        ]
        viable.sort(key=lambda m: m.cost_per_1m_input + m.cost_per_1m_output)
        return [m.to_dict() for m in viable]

    def get_model(self, name: str) -> ModelInfo | None:
        """Get model info by name."""
        for m in self._models:
            if m.name == name:
                return m
        return None

    def _task_capabilities(self, task_type: str) -> set[ModelCapability]:
        """Map task type to required capabilities."""
        task_lower = task_type.lower()
        caps: set[ModelCapability] = {ModelCapability.TEXT}
        if "code" in task_lower or "programming" in task_lower:
            caps.add(ModelCapability.CODE)
        if "reason" in task_lower or "analyz" in task_lower or "plan" in task_lower:
            caps.add(ModelCapability.REASONING)
        if "embed" in task_lower:
            caps.add(ModelCapability.EMBEDDING)
        return caps

    def _find_cheapest(
        self,
        tier: RouteTier,
        required_caps: set[ModelCapability],
        requires_session: bool,
        max_cost: float | None,
    ) -> ModelInfo | None:
        """Find cheapest model in a tier meeting all requirements."""
        candidates = [
            m for m in self._models
            if m.tier == tier
            and required_caps.issubset(m.capabilities)
            and (not requires_session or m.supports_session)
        ]
        if max_cost is not None:
            candidates = [
                m for m in candidates
                if m.cost_per_1m_input + m.cost_per_1m_output <= max_cost
            ]
        if not candidates:
            return None
        return min(candidates, key=lambda m: m.cost_per_1m_input + m.cost_per_1m_output)

    def _next_tier_model(
        self,
        current: ModelInfo,
        required_caps: set[ModelCapability],
        requires_session: bool,
        max_cost: float | None,
    ) -> str | None:
        """Find a fallback model in the next tier up."""
        tier_order = [RouteTier.LOCAL, RouteTier.CHEAP, RouteTier.STANDARD, RouteTier.PREMIUM]
        current_idx = tier_order.index(current.tier)
        if current_idx >= len(tier_order) - 1:
            return None
        next_tier = tier_order[current_idx + 1]
        next_model = self._find_cheapest(next_tier, required_caps, requires_session, max_cost)
        return next_model.name if next_model else None
