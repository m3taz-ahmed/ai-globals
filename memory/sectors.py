#!/usr/bin/env python3
"""Memory sector classification (from OpenMemory).

Classifies memory entries into 5 cognitive sectors with pattern-based
detection and sector-specific decay rates:

- Episodic: Events and experiences (decay: 0.015, weight: 1.2)
- Semantic: Facts and knowledge (decay: 0.005, weight: 1.0)
- Procedural: How-to and processes (decay: 0.008, weight: 1.1)
- Emotional: Feelings and sentiments (decay: 0.020, weight: 1.3)
- Reflective: Meta-cognition and insights (decay: 0.001, weight: 0.8)

Usage::

    from memory.sectors import SectorClassifier

    classifier = SectorClassifier()
    sector = classifier.classify("I learned how to deploy with Docker today")
    assert sector == Sector.PROCEDURAL
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum


class Sector(str, Enum):
    """5 cognitive memory sectors (from OpenMemory HMD v2)."""

    EPISODIC = "episodic"      # Events and experiences
    SEMANTIC = "semantic"      # Facts and knowledge
    PROCEDURAL = "procedural"  # How-to and processes
    EMOTIONAL = "emotional"    # Feelings and sentiments
    REFLECTIVE = "reflective"  # Meta-cognition and insights


@dataclass
class SectorConfig:
    """Configuration for a memory sector."""

    decay_lambda: float
    weight: float
    patterns: list[re.Pattern[str]]


_SECTOR_CONFIGS: dict[Sector, SectorConfig] = {
    Sector.EPISODIC: SectorConfig(
        decay_lambda=0.015,
        weight=1.2,
        patterns=[
            re.compile(r"\b(today|yesterday|tomorrow|last\s+(week|month|year))\b", re.I),
            re.compile(r"\b(remember\s+when|recall|that\s+time)\b", re.I),
            re.compile(r"\b(happened|occurred|event)\b", re.I),
        ],
    ),
    Sector.SEMANTIC: SectorConfig(
        decay_lambda=0.005,
        weight=1.0,
        patterns=[
            re.compile(r"\b(is\s+a|means|defined\s+as|refers\s+to)\b", re.I),
            re.compile(r"\b(fact|knowledge|information\s+about)\b", re.I),
            re.compile(r"\b(according\s+to|based\s+on)\b", re.I),
        ],
    ),
    Sector.PROCEDURAL: SectorConfig(
        decay_lambda=0.008,
        weight=1.1,
        patterns=[
            re.compile(r"\b(how\s+to|step\s+by\s+step|instructions)\b", re.I),
            re.compile(r"\b(First|Then|Finally|Next)\b", re.I),
            re.compile(r"\b(deploy|install|configure|setup|run)\b", re.I),
        ],
    ),
    Sector.EMOTIONAL: SectorConfig(
        decay_lambda=0.020,
        weight=1.3,
        patterns=[
            re.compile(r"\b(feel|feeling|happy|sad|angry|excited|frustrated)\b", re.I),
            re.compile(r"\b(love|hate|enjoy|dislike|amazing|terrible)\b", re.I),
        ],
    ),
    Sector.REFLECTIVE: SectorConfig(
        decay_lambda=0.001,
        weight=0.8,
        patterns=[
            re.compile(r"\b(realize|insight|pattern|lesson\s+learned)\b", re.I),
            re.compile(r"\b(I\s+think|I\s+believe|in\s+my\s+opinion)\b", re.I),
            re.compile(r"\b(reflect|consider|contemplate)\b", re.I),
        ],
    ),
}

# Cross-sector relationship weights (from OpenMemory)
SECTOR_RELATIONSHIPS: dict[Sector, dict[Sector, float]] = {
    Sector.SEMANTIC: {Sector.PROCEDURAL: 0.8, Sector.EPISODIC: 0.6, Sector.REFLECTIVE: 0.7, Sector.EMOTIONAL: 0.4},
    Sector.PROCEDURAL: {Sector.SEMANTIC: 0.8, Sector.EPISODIC: 0.6, Sector.REFLECTIVE: 0.6, Sector.EMOTIONAL: 0.3},
    Sector.EPISODIC: {Sector.SEMANTIC: 0.6, Sector.PROCEDURAL: 0.6, Sector.REFLECTIVE: 0.8, Sector.EMOTIONAL: 0.7},
    Sector.EMOTIONAL: {Sector.SEMANTIC: 0.4, Sector.PROCEDURAL: 0.3, Sector.EPISODIC: 0.7, Sector.REFLECTIVE: 0.6},
    Sector.REFLECTIVE: {Sector.SEMANTIC: 0.7, Sector.PROCEDURAL: 0.6, Sector.EPISODIC: 0.8, Sector.EMOTIONAL: 0.6},
}


@dataclass
class SectorClassifier:
    """Classify memory entries into cognitive sectors.

    Uses pattern-based detection. Falls back to SEMANTIC if no
    patterns match (semantic is the default "general knowledge" sector).
    """

    def classify(self, text: str) -> Sector:
        """Classify text into a cognitive sector."""
        scores: dict[Sector, int] = {}
        for sector, config in _SECTOR_CONFIGS.items():
            score = sum(1 for p in config.patterns if p.search(text))
            if score > 0:
                scores[sector] = score
        if not scores:
            return Sector.SEMANTIC  # Default
        return max(scores, key=lambda s: scores[s])

    def decay_score(
        self, sector: Sector, initial_salience: float, days_since: float,
    ) -> float:
        """Compute decayed salience for a sector (from OpenMemory)."""
        cfg = _SECTOR_CONFIGS[sector]
        decayed = initial_salience * math.exp(-cfg.decay_lambda * days_since)
        return max(0.0, min(1.0, decayed))

    def sector_weight(self, sector: Sector) -> float:
        """Get the weight multiplier for a sector."""
        return _SECTOR_CONFIGS[sector].weight

    def cross_sector_boost(
        self, source: Sector, target: Sector,
    ) -> float:
        """Get relationship weight between two sectors."""
        return SECTOR_RELATIONSHIPS.get(source, {}).get(target, 0.5)


if __name__ == "__main__":
    clf = SectorClassifier()
    print(f"Episodic: {clf.classify('I remember when we deployed yesterday')}")
    print(f"Procedural: {clf.classify('How to deploy: first run build, then deploy')}")
    print(f"Emotional: {clf.classify('I feel happy about the results')}")
    print(f"Reflective: {clf.classify('I realize the pattern here')}")
    print(f"Semantic: {clf.classify('Docker is a containerization platform')}")
