"""Tests for runtime/persona.py and persona integration in the kernel."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel
from runtime.persona import PersonaDetector, detect_persona


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


class TestPersonaDetector:
    def test_list_personas(self):
        d = PersonaDetector()
        assert "ARCH" in d.list_personas()
        assert len(d.list_personas()) == 9

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

    def test_run_workflow_injects_persona(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.run_workflow("test", {"message": "write unit tests for auth"})
        assert result["ok"]
        assert result["context"]["persona"] == "QA"

    def test_spawn_agent_auto_persona(self, tmp_path: Path):
        k = _kernel(tmp_path)
        result = k.spawn_agent("android-publisher", "auto", ["PublishAAB"])
        assert result["ok"]
        assert result["persona"] == "PLAY"

    def test_status_includes_personas(self, tmp_path: Path):
        k = _kernel(tmp_path)
        status = k.status()
        assert "personas" in status
        assert "ARCH" in status["personas"]
