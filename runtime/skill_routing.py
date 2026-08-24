#!/usr/bin/env python3
"""Skill routing meta-prompt and persona detection v2 (WS-I).

SKILL-W1: Routing meta-prompt — generates a structured meta-prompt that
tells the LLM which skills to activate and how to route the request.

SKILL-W2: Persona detection v2 — improved detection with confidence
scores, multi-persona support, and ambiguity detection.

Inspired by LLM-based routers (RouteLLM, FrugalGPT) and the persona
composition pattern from aiZee's existing PersonaDetector.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.persona import PersonaDetector


@dataclass
class PersonaDetectionResult:
    """SKILL-W2: Enhanced persona detection result with confidence.

    Attributes:
        primary: Primary persona code.
        personas: Ranked list of selected persona codes.
        skills: Primary skill names for selected personas.
        lords: Additional domain skills triggered.
        confidence: Detection confidence (0.0-1.0). Higher = more certain.
        ambiguous: Whether the detection is ambiguous (top-2 scores are close).
        scores: Normalized score distribution across all personas.
        reason: Human-readable explanation of the detection.
    """

    primary: str
    personas: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    lords: list[str] = field(default_factory=list)
    confidence: float = 0.0
    ambiguous: bool = False
    scores: dict[str, float] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary": self.primary,
            "personas": self.personas,
            "skills": self.skills,
            "lords": self.lords,
            "confidence": round(self.confidence, 4),
            "ambiguous": self.ambiguous,
            "scores": self.scores,
            "reason": self.reason,
        }


class PersonaDetectorV2:
    """SKILL-W2: Enhanced persona detection with confidence scoring.

    Wraps the existing PersonaDetector with:
    - Confidence scores based on score margin between top personas
    - Ambiguity detection (top-2 scores within 20% of each other)
    - Human-readable detection reasoning
    """

    AMBIGUITY_THRESHOLD = 0.2  # If top-2 scores within 20%, it's ambiguous

    def __init__(self, detector: PersonaDetector | None = None) -> None:
        self.detector = detector or PersonaDetector()

    def detect(self, text: str, max_personas: int = 3) -> PersonaDetectionResult:
        """Detect personas with confidence scoring and ambiguity detection."""
        raw = self.detector.detect_multiple(text, max_personas=max_personas)
        scores = raw.get("scores", {})
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        # Compute confidence: margin between top-1 and top-2
        if len(sorted_scores) >= 2:
            top_score = sorted_scores[0][1]
            second_score = sorted_scores[1][1]
            confidence = top_score - second_score if top_score > 0 else 0.0
            ambiguous = (top_score - second_score) < self.AMBIGUITY_THRESHOLD and top_score > 0
        elif len(sorted_scores) == 1:
            confidence = sorted_scores[0][1]
            ambiguous = False
        else:
            confidence = 0.0
            ambiguous = False
        # Build reason
        primary = raw["persona"]
        if ambiguous:
            reason = f"Ambiguous: {primary} and {sorted_scores[1][0]} scores are close"
        elif confidence > 0.5:
            reason = f"High confidence: {primary} clearly matches"
        elif confidence > 0:
            reason = f"Moderate confidence: {primary} is the best match"
        else:
            reason = f"Low confidence: using default persona {primary}"
        return PersonaDetectionResult(
            primary=primary,
            personas=raw.get("personas", []),
            skills=raw.get("skills", []),
            lords=raw.get("lords", []),
            confidence=confidence,
            ambiguous=ambiguous,
            scores=scores,
            reason=reason,
        )


class SkillRouter:
    """SKILL-W1: Generate a routing meta-prompt for skill activation.

    The meta-prompt tells the LLM which skills to activate, in what order,
    and how to route the request based on detected personas and skills.
    """

    def __init__(self, detector: PersonaDetectorV2 | None = None) -> None:
        self.detector = detector or PersonaDetectorV2()

    def route(self, text: str, max_personas: int = 3) -> dict[str, Any]:
        """Route a request to skills. Returns routing decision + meta-prompt."""
        detection = self.detector.detect(text, max_personas=max_personas)
        meta_prompt = self.build_meta_prompt(detection)
        return {
            "detection": detection.to_dict(),
            "meta_prompt": meta_prompt,
            "skills_to_load": detection.skills + detection.lords,
            "primary_persona": detection.primary,
            "ambiguous": detection.ambiguous,
        }

    def build_meta_prompt(self, detection: PersonaDetectionResult) -> str:
        """SKILL-W1: Build the routing meta-prompt.

        The meta-prompt is a structured instruction that tells the LLM:
        1. Which persona(s) are active
        2. Which skills to load
        3. How to handle ambiguity (if detected)
        4. What the routing priority is
        """
        lines: list[str] = [
            "## Skill Routing Decision",
            "",
            f"**Primary persona:** {detection.primary}",
        ]
        if detection.personas and len(detection.personas) > 1:
            lines.append(f"**Active personas:** {', '.join(detection.personas)}")
        if detection.skills:
            lines.append(f"**Skills to load:** {', '.join(detection.skills)}")
        if detection.lords:
            lines.append(f"**Domain skills:** {', '.join(detection.lords)}")
        lines.append(f"**Confidence:** {detection.confidence:.0%}")
        if detection.ambiguous:
            lines.append(
                f"**Warning:** Detection is ambiguous — {detection.reason}. "
                "Consider asking for clarification."
            )
        lines.append("")
        lines.append("### Routing Instructions")
        lines.append(f"1. Load and apply the primary skill: **{detection.skills[0] if detection.skills else 'default'}**")
        if len(detection.skills) > 1:
            for i, skill in enumerate(detection.skills[1:], start=2):
                lines.append(f"{i}. Apply secondary skill: **{skill}**")
        if detection.lords:
            next_idx = len(detection.skills) + 1
            for lord in detection.lords:
                lines.append(f"{next_idx}. Apply domain skill: **{lord}**")
                next_idx += 1
        if detection.ambiguous:
            next_idx = len(detection.skills) + len(detection.lords) + 1
            lines.append(f"{next_idx}. If the request is unclear, ask the user to clarify their intent.")
        return "\n".join(lines)
