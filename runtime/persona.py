"""Persona detection and skill composition for AI Global OS."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

from runtime.skill_resolver import SkillResolver


def _load_persona_data() -> dict[str, Any]:
    """Load persona and lord skill definitions from personas.yaml."""
    data_path = Path(__file__).resolve().parent / "personas.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], data)


class PersonaDetector:
    """Map user prompts to one or more AI Global OS personas and related skills.

    The detector uses weighted keyword matching for personas and a separate
    keyword index for domain ("lord") skills. Results compose a primary persona,
    a ranked list of personas, and a list of skill names that should be loaded.
    """

    _DATA: ClassVar[dict[str, Any]] = _load_persona_data()
    DEFAULT: ClassVar[str] = _DATA["default"]
    PERSONA_LORD_BONUS: ClassVar[float] = _DATA["persona_lord_bonus"]
    PERSONAS: ClassVar[dict[str, dict[str, Any]]] = _DATA["personas"]
    LORD_SKILLS: ClassVar[dict[str, list[str]]] = _DATA["lord_skills"]

    def __init__(self, default: str = DEFAULT, skill_resolver: SkillResolver | None = None) -> None:
        if default not in self.PERSONAS:
            raise ValueError(f"Unknown default persona: {default}")
        self.default = default
        self.skill_resolver = skill_resolver or SkillResolver()

    def list_personas(self) -> list[str]:
        """Return all defined persona codes."""
        return list(self.PERSONAS.keys())

    def list_lord_skills(self) -> list[str]:
        """Return all known lord skill names."""
        return list(self.LORD_SKILLS.keys())

    def skill_for(self, persona: str) -> str:
        """Primary skill name for a persona code."""
        return cast(str, self.PERSONAS.get(persona, self.PERSONAS[self.default])["skill"])

    def _is_active_skill(self, name: str, context: dict[str, Any]) -> bool:
        """Return True if the skill is active for the context or not on disk."""
        if self.skill_resolver.resolve_with_frontmatter(name, context) is not None:
            return True
        return not self.skill_resolver.exists(name)

    def _keyword_match(self, text: str, keyword: str) -> bool:
        """Match a keyword as a whole word/phrase to avoid substring false positives."""
        pattern = r"\b" + re.escape(keyword) + r"\b"
        return bool(re.search(pattern, text, re.IGNORECASE))

    def _score_personas(self, text: str) -> dict[str, float]:
        scores: dict[str, float] = {}
        for code, info in self.PERSONAS.items():
            score = 0.0
            for kw in info["keywords"]:
                if self._keyword_match(text, kw):
                    score += info["weight"]
            scores[code] = round(score, 3)
        return scores

    def _lord_matches(self, text: str, skill: str) -> int:
        """Count how many of a lord skill's keywords appear in the prompt."""
        return sum(1 for kw in self.LORD_SKILLS.get(skill, []) if self._keyword_match(text, kw))

    def _detect_lords(self, text: str) -> list[str]:
        """Return lord skills whose keywords appear in the prompt."""
        matched: set[str] = set()
        for skill in self.LORD_SKILLS:
            if self._lord_matches(text, skill):
                matched.add(skill)
        return sorted(matched)

    def detect_multiple(
        self,
        text: str,
        max_personas: int = 3,
        max_lords: int = 5,
        include_lords: bool = True,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Detect the top N personas and the skill set they compose.

        The returned dict contains:
        - persona: primary persona code
        - personas: ranked list of selected persona codes
        - skill: primary skill name
        - skills: primary skill names for selected personas
        - lords: additional domain skills triggered by the prompt or persona
        - scores: normalized score distribution across all personas
        - default: the default persona code
        """
        scores = self._score_personas(text)
        sorted_personas = sorted(scores, key=lambda k: scores[k], reverse=True)
        selected = [p for p in sorted_personas if scores[p] > 0][:max_personas]
        if not selected:
            selected = [self.default]

        primary = selected[0]

        skill_context = dict(context or {})
        if "persona" not in skill_context and "personas" not in skill_context:
            skill_context["persona"] = primary
            skill_context["personas"] = selected

        primary_skills: list[str] = []
        seen_skills: set[str] = set()
        for p in selected:
            sk = self.skill_for(p)
            if sk in seen_skills or not self._is_active_skill(sk, skill_context):
                continue
            seen_skills.add(sk)
            primary_skills.append(sk)

        lord_scores: dict[str, float] = {}
        if include_lords:
            for p in selected:
                for lord in self.PERSONAS[p].get("lords", []):
                    lord_scores[lord] = lord_scores.get(lord, 0.0) + self.PERSONA_LORD_BONUS
            for skill in self.LORD_SKILLS:
                matches = self._lord_matches(text, skill)
                if matches:
                    lord_scores[skill] = lord_scores.get(skill, 0.0) + matches

        # Lords that duplicate an active primary skill are promoted to the primary list.
        ranked_lords = sorted(
            (
                (lord, score)
                for lord, score in lord_scores.items()
                if lord not in seen_skills and self._is_active_skill(lord, skill_context)
            ),
            key=lambda x: (-x[1], x[0]),
        )
        lords = [lord for lord, _ in ranked_lords[:max_lords]]

        total = sum(scores.values()) or 1.0
        normalized = {k: round(v / total, 3) for k, v in scores.items()}

        return {
            "persona": primary,
            "personas": selected,
            "skill": primary_skills[0] if primary_skills else self.skill_for(self.default),
            "skills": primary_skills,
            "lords": lords,
            "scores": normalized,
            "default": self.default,
        }

    def detect(self, text: str) -> dict[str, Any]:
        """Backwards-compatible single-persona detection."""
        result = self.detect_multiple(text, max_personas=1, include_lords=False)
        return {
            "persona": result["persona"],
            "skill": result["skill"],
            "scores": result["scores"],
            "default": result["default"],
        }

    def resolve_skills(
        self,
        personas: Iterable[str],
        lords: Iterable[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[str]:
        """Return unique, active skill names for the given personas and lords."""
        active_context = context or {}
        names: list[str] = [self.skill_for(p) for p in personas]
        if lords:
            names.extend(lords)
        seen: set[str] = set()
        valid: list[str] = []
        for name in names:
            if name in seen or self.skill_resolver.resolve_with_frontmatter(name, active_context) is None:
                continue
            seen.add(name)
            valid.append(name)
        return valid


def detect_persona(text: str, default: str = "ARCH") -> str:
    """Convenience helper that returns only the persona code."""
    return cast(str, PersonaDetector(default).detect(text)["persona"])
