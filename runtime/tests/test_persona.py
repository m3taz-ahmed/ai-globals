"""Tests for runtime/persona.py, runtime/skill_resolver.py, and persona integration in the kernel."""

from __future__ import annotations

from pathlib import Path

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
        assert len(d.list_personas()) == 18

    def test_unknown_default_raises(self):
        try:
            PersonaDetector(default="UNKNOWN")
        except ValueError as e:
            assert "Unknown default persona" in str(e)
        else:
            raise AssertionError("expected ValueError")

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
        assert result["persona"] == "PROPOSAL"
        assert result["skill"] == "proposal-writer"

    def test_detects_proposal_arabic(self):
        d = PersonaDetector()
        result = d.detect("عايز بروبوزل للموقع بتاعي بالعربي والإنجليزي")
        assert result["persona"] == "PROPOSAL"
        assert result["skill"] == "proposal-writer"


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
