"""Gap tests for eval/harness.py."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from eval.harness import EvalHarness, EvidenceGates, GateName


class TestEvidenceGates:
    def test_all_pass(self):
        g = EvidenceGates()
        g.run_all(["a"], {"check": True}, ["pytest"], "revert commit", "summary")
        assert g.all_passed
        assert len(g.results) == 5
        assert g.to_dict()[0]["name"] == "scope"

    def test_scope_fail_stops(self):
        g = EvidenceGates()
        g.run_all([], {"c": True}, ["x"], "r", "s")
        assert len(g.results) == 1
        assert g.results[0].name is GateName.SCOPE

    def test_quality_fail_stops(self):
        g = EvidenceGates()
        g.run_all(["a"], {"c": False}, ["x"], "r", "s")
        assert len(g.results) == 2
        assert not g.all_passed

    def test_evidence_fail_stops(self):
        g = EvidenceGates()
        g.run_all(["a"], {"c": True}, [], "r", "s")
        assert len(g.results) == 3

    def test_risk_fail_stops(self):
        g = EvidenceGates()
        g.run_all(["a"], {"c": True}, ["x"], "  ", "s")
        assert len(g.results) == 4

    def test_communication_empty_summary(self):
        g = EvidenceGates()
        g.run_all(["a"], {"c": True}, ["x"], "revert", "")
        assert len(g.results) == 5
        assert not g.all_passed


class TestHarnessRun:
    def test_run_missing_tool(self, tmp_path):
        h = EvalHarness(tmp_path)
        out = h._run("nonexistent-tool", ["this_tool_does_not_exist_xyz"])
        assert out["ok"] is False
        assert out["returncode"] == -1

    def test_run_captures(self, tmp_path):
        h = EvalHarness(tmp_path)
        p = MagicMock(returncode=0, stdout="out", stderr="err")
        with patch("eval.harness.subprocess.run", return_value=p):
            out = h._run("x", ["cmd"])
        assert out["returncode"] == 0
        assert "out" in out["output"] and "err" in out["output"]

    def test_full_run_aggregates(self, tmp_path):
        h = EvalHarness(tmp_path)
        calls = []
        def fake_run(name, cmd):
            calls.append(name)
            return {"returncode": 0, "output": "ok"}
        with patch.object(EvalHarness, "_run", side_effect=fake_run):
            out = h.run()
        assert out["all_pass"] is True
        assert set(calls) == {"ruff", "mypy", "pytest", "validate-globals"}

    def test_full_run_failure(self, tmp_path):
        h = EvalHarness(tmp_path)
        def fake_run(name, cmd):
            return {"returncode": 1 if name == "ruff" else 0, "output": ""}
        with patch.object(EvalHarness, "_run", side_effect=fake_run):
            out = h.run()
        assert out["all_pass"] is False

    def test_evidence_gates_wrapper(self, tmp_path):
        h = EvalHarness(tmp_path)
        out = h.run_evidence_gates(["a"], {"c": True}, ["cmd"], "rb", "sum")
        assert out["all_passed"] is True
        assert len(out["gates"]) == 5


class TestXdistDetection:
    def test_pytest_cmd_without_xdist(self, tmp_path):
        """Cover the find_spec('xdist') is None branch: no -n flag appended."""
        h = EvalHarness(tmp_path)
        cmds: dict[str, list[str]] = {}

        def fake_run(name, cmd):
            cmds[name] = cmd
            return {"returncode": 0, "output": "ok"}

        with (
            patch.object(EvalHarness, "_run", side_effect=fake_run),
            patch("importlib.util.find_spec", return_value=None),
        ):
            h.run()
        assert "-n" not in cmds["pytest"]
