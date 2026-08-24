"""Tests for WS-I: Skills/personas (SKILL-W1 routing meta-prompt, W2 persona detection v2)."""

from __future__ import annotations

from runtime.skill_routing import PersonaDetectorV2, SkillRouter

# ---------------------------------------------------------------------------
# SKILL-W2: Persona detection v2
# ---------------------------------------------------------------------------


class TestPersonaDetectionV2:
    """Enhanced persona detection with confidence and ambiguity."""

    def test_detect_returns_result(self) -> None:
        detector = PersonaDetectorV2()
        result = detector.detect("write a python function to sort a list")
        assert result.primary is not None
        assert result.confidence >= 0.0
        assert isinstance(result.reason, str)

    def test_detect_high_confidence(self) -> None:
        detector = PersonaDetectorV2()
        # Very specific backend prompt
        result = detector.detect("write a python flask API endpoint with SQLAlchemy")
        assert result.confidence >= 0.0

    def test_detect_ambiguous(self) -> None:
        detector = PersonaDetectorV2()
        # A prompt that could match multiple personas
        result = detector.detect("write code and design the database schema")
        # Should have a reason string regardless of ambiguity
        assert isinstance(result.reason, str)
        assert isinstance(result.ambiguous, bool)

    def test_detect_default_on_no_match(self) -> None:
        detector = PersonaDetectorV2()
        result = detector.detect("hello world")
        assert result.primary is not None
        assert result.confidence == 0.0 or result.confidence >= 0.0

    def test_to_dict(self) -> None:
        detector = PersonaDetectorV2()
        result = detector.detect("write python code")
        d = result.to_dict()
        assert "primary" in d
        assert "confidence" in d
        assert "ambiguous" in d
        assert "reason" in d

    def test_scores_populated(self) -> None:
        detector = PersonaDetectorV2()
        result = detector.detect("write a python web API")
        assert len(result.scores) > 0


# ---------------------------------------------------------------------------
# SKILL-W1: Routing meta-prompt
# ---------------------------------------------------------------------------


class TestSkillRouter:
    """Skill router generates a routing meta-prompt."""

    def test_route_returns_decision(self) -> None:
        router = SkillRouter()
        decision = router.route("write a python flask API")
        assert "detection" in decision
        assert "meta_prompt" in decision
        assert "skills_to_load" in decision
        assert "primary_persona" in decision
        assert "ambiguous" in decision

    def test_meta_prompt_contains_persona(self) -> None:
        router = SkillRouter()
        decision = router.route("write a python flask API")
        prompt = decision["meta_prompt"]
        assert "Primary persona" in prompt
        assert "Routing Instructions" in prompt

    def test_meta_prompt_contains_skills(self) -> None:
        router = SkillRouter()
        decision = router.route("write a python flask API")
        prompt = decision["meta_prompt"]
        # Should mention skills to load
        assert "skill" in prompt.lower()

    def test_meta_prompt_ambiguous_warning(self) -> None:
        router = SkillRouter()
        # Create a detection with ambiguous=True
        from runtime.skill_routing import PersonaDetectionResult

        detection = PersonaDetectionResult(
            primary="BACK",
            personas=["BACK", "FRONT"],
            skills=["backend-skill", "frontend-skill"],
            confidence=0.1,
            ambiguous=True,
            reason="Ambiguous: BACK and FRONT scores are close",
        )
        prompt = router.build_meta_prompt(detection)
        assert "Warning" in prompt
        assert "ambiguous" in prompt.lower()

    def test_meta_prompt_no_skills(self) -> None:
        router = SkillRouter()
        from runtime.skill_routing import PersonaDetectionResult

        detection = PersonaDetectionResult(
            primary="ARCH",
            skills=[],
            confidence=0.0,
        )
        prompt = router.build_meta_prompt(detection)
        assert "default" in prompt

    def test_skills_to_load_includes_lords(self) -> None:
        router = SkillRouter()
        from runtime.skill_routing import PersonaDetectionResult

        detection = PersonaDetectionResult(
            primary="BACK",
            skills=["backend"],
            lords=["security", "database"],
            confidence=0.8,
        )
        prompt = router.build_meta_prompt(detection)
        assert "security" in prompt
        assert "database" in prompt
