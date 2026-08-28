"""Persona detection and skill composition for aiZee."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

from runtime.skill_resolver import SkillResolver


def _load_persona_data() -> dict[str, Any]:
    """Load persona and lord skill definitions from personas.yaml."""
    data_path = Path(__file__).resolve().parent / "personas.yaml"
    data = yaml.safe_load(data_path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], data)


# -- Persona Reset Triggers --------------------------------------------------
# Short commands (English + Arabic) that force persona re-detection mid-chat.
# Matched as standalone commands — must be the whole message or start with
# the trigger followed by optional extra text (e.g., "/reset to backend").
RESET_TRIGGERS: set[str] = {
    # English slash commands
    "/reset",
    "/persona",
    "/redetect",
    "/switch",
    # English hashtag commands
    "#reset",
    "#persona",
    "#redetect",
    "#switch",
    # Arabic slash commands
    "/انتحل",
    "/شخصيات",
    "/بدّل",
    "/بدل",
    "/تصحيح-الشخصية",
    # Arabic hashtag commands
    "#انتحل",
    "#شخصيات",
    "#بدّل",
    "#بدل",
}

_RESET_PATTERN = re.compile(
    r"^(?:" + "|".join(re.escape(t) for t in RESET_TRIGGERS) + r")\b",
    re.IGNORECASE,
)


def is_persona_reset_command(text: str) -> bool:
    """True if *text* is a persona reset trigger command.

    Matches standalone commands like ``/reset``, ``#انتحل``, or the same
    command followed by extra context (e.g., ``/reset to backend mode``).
    """
    if not text or not text.strip():
        return False
    return bool(_RESET_PATTERN.match(text.strip()))


# -- Persona Status Triggers -------------------------------------------------
# Short commands that request a formatted display of the currently active
# personas, their skills, and lord skills — without re-detecting.
STATUS_TRIGGERS: set[str] = {
    # English slash commands
    "/status",
    "/info",
    "/whoami",
    "/current",
    # English hashtag commands
    "#status",
    "#info",
    "#whoami",
    "#current",
    # Arabic slash commands
    "/حالة",
    "/مين",
    "/شخصية-الحالية",
    "/معلومات",
    # Arabic hashtag commands
    "#حالة",
    "#مين",
    "#شخصية-الحالية",
    "#معلومات",
}

_STATUS_PATTERN = re.compile(
    r"^(?:" + "|".join(re.escape(t) for t in STATUS_TRIGGERS) + r")\s*$",
    re.IGNORECASE,
)


def is_persona_status_command(text: str) -> bool:
    """True if *text* is a persona status query command.

    Matches standalone commands only (no extra text) like ``/status``,
    ``#حالة``, ``/whoami``. Unlike reset commands, status commands must
    be the entire message — no trailing hint text.
    """
    if not text or not text.strip():
        return False
    return bool(_STATUS_PATTERN.match(text.strip()))


def _load_skill_description(name: str, skills_dir: Path) -> str:
    """Load a skill's description from its frontmatter (best-effort)."""
    for candidate in (skills_dir / f"{name}.md", skills_dir / name / "SKILL.md"):
        if candidate.is_file():
            try:
                text = candidate.read_text(encoding="utf-8")
                parts = text.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1])
                    if isinstance(fm, dict):
                        return str(fm.get("description", "")).strip()
            except (OSError, yaml.YAMLError):
                pass
    return ""


def format_persona_status(
    context: dict[str, Any],
    detector: PersonaDetector,
    skills_dir: Path | None = None,
) -> str:
    """Format the current persona/skill state as a compact, organized report.

    Args:
        context: The runtime context containing persona/skills/lords fields.
        detector: The PersonaDetector for looking up persona metadata.
        skills_dir: Optional skills directory for loading descriptions.
            If None, uses the detector's skill_resolver root.

    Returns:
        A formatted multi-line string with persona names, skills, and lords.
    """
    if skills_dir is None:
        skills_dir = detector.skill_resolver.skills_dir

    personas: list[str] = list(context.get("personas", []))
    primary: str = str(context.get("persona", ""))
    skills: list[str] = list(context.get("skills", []))
    lords: list[str] = list(context.get("lords", []))

    if not primary and not personas:
        return "⚠️ لم يتم تحديد أي شخصية بعد. أرسل رسالة أو استخدم /reset لبدء الكشف."

    lines: list[str] = ["═" * 60, "🎯 الشخصيات والتقنيات النشطة", "═" * 60]

    # Primary persona
    if primary:
        info = detector.PERSONAS.get(primary, {})
        name = str(info.get("name", primary))
        weight = info.get("weight", 1.0)
        lines.append(f"\n👤 الشخصية الأساسية: {primary}")
        lines.append(f"   الاسم: {name}")
        lines.append(f"   الوزن: {weight}")

    # Secondary personas
    if personas and personas != [primary]:
        lines.append(f"\n👥 الشخصيات الإضافية: {', '.join(personas)}")

    # Primary skills
    if skills:
        lines.append(f"\n🛠️ المهارات الأساسية ({len(skills)}):")
        for sk in skills:
            desc = _load_skill_description(sk, skills_dir)
            if desc:
                # Truncate description to ~80 chars for compactness
                short_desc = desc[:80] + ("…" if len(desc) > 80 else "")
                lines.append(f"   • {sk}: {short_desc}")
            else:
                lines.append(f"   • {sk}")

    # Lord skills (domain specialists)
    if lords:
        lines.append(f"\n⚡ مهارات اللوردات ({len(lords)}):")
        for lord in lords:
            desc = _load_skill_description(lord, skills_dir)
            if desc:
                short_desc = desc[:80] + ("…" if len(desc) > 80 else "")
                lines.append(f"   • {lord}: {short_desc}")
            else:
                lines.append(f"   • {lord}")

    lines.append(f"\n{'─' * 60}")
    lines.append("📋 استخدم /reset أو /انتحل لإعادة الكشف")
    lines.append(f"{'═' * 60}")
    return "\n".join(lines)


def inject_persona_context(
    detector: PersonaDetector,
    context: dict[str, Any],
    text_keys: Sequence[str] = ("message", "request", "query", "content"),
    fallback_text: str | None = None,
) -> dict[str, Any]:
    """Populate persona/skill fields in *context* from the first text key found.

    Single source of truth for the persona-injection block previously
    duplicated across Kernel._auto_persona, WorkflowManager.run_workflow,
    and WorkflowRunner.run. Mutates and returns *context*; no-op when
    persona fields already exist or no usable text is present.

    **Reset triggers:** If the extracted text is a persona reset command
    (e.g., ``/reset``, ``#انتحل``), any existing persona fields are cleared
    and re-detection runs against the full text (including any hint after
    the command, e.g., ``/reset to backend`` → re-detect with "backend").
    """
    text: Any = fallback_text
    for key in text_keys:
        value = context.get(key)
        if isinstance(value, str):
            text = value
            break
    if not isinstance(text, str) or not text.strip():
        return context

    # Status trigger: format current persona state without re-detecting.
    if is_persona_status_command(text):
        context["persona_status"] = format_persona_status(context, detector)
        return context

    # Reset trigger: clear existing persona fields and re-detect.
    if is_persona_reset_command(text):
        for key in ("persona", "skill", "personas", "skills", "lords"):
            context.pop(key, None)

    # Normal path: skip if persona already set (unless reset was triggered).
    if "personas" in context or "persona" in context:
        return context

    result = detector.detect_multiple(text)
    context["persona"] = result["persona"]
    context["skill"] = result["skill"]
    context["personas"] = result["personas"]
    context["skills"] = result["skills"]
    context["lords"] = result["lords"]
    return context


class PersonaDetector:
    """Map user prompts to one or more aiZee personas and related skills.

    The detector uses weighted keyword matching for personas and a separate
    keyword index for domain ("lord") skills. Results compose a primary persona,
    a ranked list of personas, and a list of skill names that should be loaded.
    """

    _DATA: ClassVar[dict[str, Any]] = _load_persona_data()
    DEFAULT: ClassVar[str] = _DATA["default"]
    PERSONA_LORD_BONUS: ClassVar[float] = _DATA["persona_lord_bonus"]
    PERSONAS: ClassVar[dict[str, dict[str, Any]]] = _DATA["personas"]
    LORD_SKILLS: ClassVar[dict[str, list[str]]] = _DATA["lord_skills"]
    # Pre-compiled regex cache for keyword matching (compiled once at class load)
    _COMPILED_KEYWORDS: ClassVar[dict[str, re.Pattern[str]]] = {
        kw.lower(): re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for info in _DATA["personas"].values()
        for kw in info.get("keywords", [])
    } | {
        kw.lower(): re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for kws in _DATA.get("lord_skills", {}).values()
        for kw in kws
    }

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
        pat = self._COMPILED_KEYWORDS.get(keyword.lower())
        if pat is not None:
            return bool(pat.search(text))
        # Fallback for keywords not in cache (dynamic lord skills)
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
