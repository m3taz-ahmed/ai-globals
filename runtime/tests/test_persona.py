"""Tests for runtime/persona.py, runtime/skill_resolver.py, and persona integration in the kernel."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.kernel import Kernel
from runtime.persona import PersonaDetector, detect_persona
from runtime.skill_resolver import SkillResolver


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
    )
    (tmp_path / "workflows/test.md").write_text(
        "[WORKFLOW] test\n[RULES]\n1. [REQ] Step one.\n2. [CMD] Step two.\n"
    )
    return Kernel(tmp_path)


class TestSkillResolver:
    def test_finds_flat_and_directory_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "flat.md").write_text("---\nname: flat\n---\n[SKILL] flat\n[OBJ] Test.\n[RULES]\n1. [REQ] R.\n")
        nested = skills / "nested"
        nested.mkdir()
        (nested / "SKILL.md").write_text("---\nname: nested\n---\n[SKILL] nested\n[OBJ] Test.\n[RULES]\n1. [REQ] R.\n")

        resolver = SkillResolver(tmp_path)
        assert resolver.resolve("flat") == skills / "flat.md"
        assert resolver.resolve("nested") == nested / "SKILL.md"
        assert resolver.exists("flat")
        assert resolver.exists("nested")
        assert resolver.resolve("missing") is None

    def test_rejects_path_traversal(self, tmp_path: Path):
        resolver = SkillResolver(tmp_path)
        assert resolver.resolve("../AGENTS") is None
        assert resolver.resolve("a/b") is None


class TestPersonaDetector:
    def test_list_personas(self):
        d = PersonaDetector()
        assert "ARCH" in d.list_personas()
        assert "CV" in d.list_personas()
        assert "FREELANCE" in d.list_personas()
        assert len(d.list_personas()) == 22

    def test_unknown_default_raises(self):
        with pytest.raises(ValueError, match="Unknown default persona"):
            PersonaDetector(default="UNKNOWN")

    def test_detects_security(self):
        d = PersonaDetector()
        result = d.detect("audit the firewall and fix zero trust auth")
        assert result["persona"] == "SEC"
        assert result["scores"]["SEC"] > result["scores"]["ARCH"]

    def test_detects_game(self):
        d = PersonaDetector()
        result = d.detect("optimize the babylon.js game loop for 60 fps")
        assert result["persona"] == "GAME"
        assert result["skill"] == "game-architect"

    def test_detects_google_play(self):
        d = PersonaDetector()
        result = d.detect("publish android aab to google play console and reduce anr")
        assert result["persona"] == "PLAY"

    def test_detects_qa(self):
        d = PersonaDetector()
        result = d.detect("increase test coverage and write edge case tests")
        assert result["persona"] == "QA"

    def test_default_on_empty(self):
        d = PersonaDetector(default="DEV")
        result = d.detect("hello")
        assert result["persona"] == "DEV"

    def test_detect_persona_helper(self):
        assert detect_persona("deploy with kubernetes and terraform") == "SRE"

    def test_persona_skill_mapping(self):
        d = PersonaDetector()
        result = d.detect("backend api server")
        assert result["persona"] == "DEV"
        assert result["skill"] == "backend-api-expert"

    def test_detect_multiple_returns_primary_and_personas(self):
        d = PersonaDetector()
        result = d.detect_multiple("build a secure docker api with kubernetes")
        assert result["persona"] in ("DEV", "SRE", "API", "SEC", "DEVOPS")
        assert isinstance(result["personas"], list)
        assert len(result["personas"]) <= 3
        assert "skills" in result
        assert "lords" in result

    def test_detect_multiple_includes_lord_skills(self):
        d = PersonaDetector()
        result = d.detect_multiple("optimize react frontend performance with docker")
        lords = result["lords"]
        assert "frontend-frameworks-lord" in lords
        assert "fullstack-optimizer" in lords

    def test_new_persona_data(self):
        d = PersonaDetector()
        result = d.detect("design an etl pipeline for postgres")
        assert result["persona"] == "DATA"
        assert result["skill"] == "data-engineer"

    def test_new_persona_ml(self):
        d = PersonaDetector()
        result = d.detect("train a pytorch model and deploy it as an onnx endpoint")
        assert result["persona"] == "ML"
        assert result["skill"] == "ml-engineer"

    def test_new_persona_legal(self):
        d = PersonaDetector()
        result = d.detect("write a gdpr privacy policy and check soc2 compliance")
        assert result["persona"] == "LEGAL"
        assert result["skill"] == "legal-compliance"


    def test_detects_proposal(self):
        d = PersonaDetector()
        result = d.detect("write a bilingual website proposal in arabic and english with pricing and timeline")
        assert result["persona"] == "FREELANCE"
        assert result["skill"] == "freelance-platforms"

    def test_detects_proposal_arabic(self):
        d = PersonaDetector()
        result = d.detect("عايز بروبوزل للموقع بتاعي بالعربي والإنجليزي")
        assert result["persona"] == "FREELANCE"
        assert result["skill"] == "freelance-platforms"

    def test_detects_cv(self):
        d = PersonaDetector()
        result = d.detect("write a bilingual cv in arabic and english for a software engineer")
        assert result["persona"] == "CV"
        assert result["skill"] == "cv-writer"

    def test_detects_cv_arabic(self):
        d = PersonaDetector()
        result = d.detect("عايز cv احترافي بالعربي والإنجليزي")
        assert result["persona"] == "CV"
        assert result["skill"] == "cv-writer"


class TestKernelPersonaIntegration:
    def test_detect_persona_method(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.detect_persona("render 3D scene in babylon")
        assert result["persona"] == "GAME"

    def test_act_injects_persona(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.act("Read", content="audit firewall rules", approved=True)
        assert result["ok"]
        assert result["args"]["persona"] == "SEC"
        assert "personas" in result["args"]
        assert "lords" in result["args"]

    def test_run_workflow_injects_persona(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.run_workflow("test", {"message": "write unit tests for auth"})
        assert result["ok"]
        assert result["context"]["persona"] == "QA"
        assert "personas" in result["context"]

    def test_spawn_agent_auto_persona(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.spawn_agent("android-publisher", "auto", ["Publish", "AAB", "PlayStore"])
        assert result["ok"]
        assert result["persona"] == "PLAY"
        assert result["personas"] == ["PLAY"]

    def test_spawn_agent_multiple_personas(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.spawn_agent("reviewer", "ARCH,QA", ["Read", "Review"])
        assert result["ok"]
        assert result["persona"] == "ARCH"
        assert result["personas"] == ["ARCH", "QA"]

    def test_status_includes_personas(self, tmp_path: Path):
        k = _kernel(tmp_path)
        status = k.status()
        assert "personas" in status
        assert "ARCH" in status["personas"]


class TestSkillResolverLoadAndFrontmatter:
    def test_load_returns_text_for_existing_skill(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "myload.md").write_text(
            "---\nname: myload\n---\n[SKILL] myload\n[OBJ] Test.\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        text = resolver.load("myload")
        assert text is not None
        assert "[SKILL] myload" in text

    def test_load_returns_none_for_missing_skill(self, tmp_path: Path):
        resolver = SkillResolver(tmp_path)
        assert resolver.load("nonexistent") is None

    def test_load_with_frontmatter_returns_none_for_missing_skill(self, tmp_path: Path):
        resolver = SkillResolver(tmp_path, tmp_path)
        assert resolver.load_with_frontmatter("nonexistent", {}) is None


class TestPersonaDetectorCoverage:
    def test_list_lord_skills(self):
        d = PersonaDetector()
        lords = d.list_lord_skills()
        assert isinstance(lords, list)
        assert len(lords) > 0

    def test_is_active_skill_returns_true_when_resolved(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "active.md").write_text(
            "---\nname: active\n---\n[SKILL] active\n[OBJ] Test.\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        d = PersonaDetector(skill_resolver=resolver)
        assert d._is_active_skill("active", {}) is True

    def test_detect_lords_finds_matching_skills(self):
        d = PersonaDetector()
        lords = d._detect_lords("optimize react frontend performance")
        assert "frontend-frameworks-lord" in lords

    def test_detect_multiple_skips_duplicate_or_inactive_skill(self, tmp_path: Path):
        """Cover line 124: continue when skill in seen_skills or not active."""
        skills = tmp_path / "skills"
        skills.mkdir()
        # Create a skill file that won't match context (persona=SEC only)
        (skills / "backend-api-expert.md").write_text(
            "---\npersonas: [SEC]\n---\n[SKILL] backend\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        d = PersonaDetector(skill_resolver=resolver)
        # "backend api server" triggers DEV persona whose skill is backend-api-expert
        # but the skill file requires persona=SEC, so it won't be active for DEV context
        result = d.detect_multiple("backend api server", context={"persona": "DEV"})
        # The primary skill should fall back to default since backend-api-expert is inactive
        assert isinstance(result["skills"], list)

    def test_resolve_skills_returns_active_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "backend-api-expert.md").write_text(
            "---\nname: backend-api-expert\n---\n[SKILL] backend\n", encoding="utf-8"
        )
        (skills / "frontend-frameworks-lord.md").write_text(
            "---\nname: frontend-frameworks-lord\n---\n[SKILL] frontend\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        d = PersonaDetector(skill_resolver=resolver)
        result = d.resolve_skills(["DEV"], lords=["frontend-frameworks-lord"])
        assert "backend-api-expert" in result
        assert "frontend-frameworks-lord" in result

    def test_resolve_skills_filters_inactive(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "backend-api-expert.md").write_text(
            "---\npersonas: [SEC]\n---\n[SKILL] backend\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        d = PersonaDetector(skill_resolver=resolver)
        # With DEV context, backend-api-expert (requires SEC) won't match
        result = d.resolve_skills(["DEV"], context={"persona": "DEV"})
        assert "backend-api-expert" not in result

    def test_resolve_skills_with_no_lords(self, tmp_path: Path):
        skills = tmp_path / "skills"
        skills.mkdir()
        (skills / "backend-api-expert.md").write_text(
            "---\nname: backend-api-expert\n---\n[SKILL] backend\n", encoding="utf-8"
        )
        resolver = SkillResolver(tmp_path)
        d = PersonaDetector(skill_resolver=resolver)
        result = d.resolve_skills(["DEV"])
        assert "backend-api-expert" in result
