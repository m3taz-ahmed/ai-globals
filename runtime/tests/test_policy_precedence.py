"""Tests for GATE-B3: policy precedence, default_action immutability, _MISSING sentinel."""

from __future__ import annotations

from pathlib import Path

from runtime.policy import PolicyEngine, _SafeEvaluator


class TestMissingSentinel:
    """_MISSING sentinel prevents allow-by-absence in != comparisons."""

    def test_ne_string_missing_attr_does_not_match(self) -> None:
        """env != 'prod' must NOT match when env is absent (GATE-06)."""
        ev = _SafeEvaluator({"type": "exec"})
        assert ev.evaluate("env != 'prod'") is False

    def test_ne_string_present_attr_matches(self) -> None:
        ev = _SafeEvaluator({"type": "exec", "env": "staging"})
        assert ev.evaluate("env != 'prod'") is True

    def test_ne_string_present_attr_does_not_match(self) -> None:
        ev = _SafeEvaluator({"type": "exec", "env": "prod"})
        assert ev.evaluate("env != 'prod'") is False

    def test_eq_missing_attr_does_not_match(self) -> None:
        ev = _SafeEvaluator({"type": "exec"})
        assert ev.evaluate("env == 'prod'") is False

    def test_in_missing_attr_does_not_match(self) -> None:
        ev = _SafeEvaluator({"type": "exec"})
        assert ev.evaluate("'prod' in env_list") is False


class TestPolicyPrecedence:
    """Rules with higher priority win; ties broken by file order."""

    def _make_engine(self, tmp_path: Path, rules_yaml: str) -> PolicyEngine:
        pdir = tmp_path / "runtime" / "policies"
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "default.yaml").write_text("default_action: ask\nrules: []\n")
        (pdir / "test.yaml").write_text(rules_yaml)
        return PolicyEngine(tmp_path)

    def test_higher_priority_wins(self, tmp_path: Path) -> None:
        yaml = (
            "rules:\n"
            "  - name: low-priority-allow\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: allow\n"
            "    priority: 1\n"
            "  - name: high-priority-deny\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: deny\n"
            "    priority: 10\n"
        )
        engine = self._make_engine(tmp_path, yaml)
        result = engine.can("exec")
        assert result["decision"] == "deny"
        assert result["rule"] == "high-priority-deny"

    def test_tie_breaks_by_file_order(self, tmp_path: Path) -> None:
        yaml = (
            "rules:\n"
            "  - name: first-allow\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: allow\n"
            "    priority: 5\n"
            "  - name: second-deny\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: deny\n"
            "    priority: 5\n"
        )
        engine = self._make_engine(tmp_path, yaml)
        result = engine.can("exec")
        # Same priority → first one wins (file order)
        assert result["decision"] == "allow"
        assert result["rule"] == "first-allow"

    def test_default_priority_is_zero(self, tmp_path: Path) -> None:
        yaml = (
            "rules:\n"
            "  - name: no-priority\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: deny\n"
            "  - name: has-priority\n"
            "    condition: \"type == 'exec'\"\n"
            "    action: allow\n"
            "    priority: 1\n"
        )
        engine = self._make_engine(tmp_path, yaml)
        result = engine.can("exec")
        assert result["decision"] == "allow"
        assert result["rule"] == "has-priority"


class TestDefaultActionImmutability:
    """Non-default YAML files must NOT clobber default_action."""

    def test_non_default_yaml_cannot_set_default_action(self, tmp_path: Path) -> None:
        import warnings

        pdir = tmp_path / "runtime" / "policies"
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "default.yaml").write_text("default_action: ask\nrules: []\n")
        (pdir / "zzz_last.yaml").write_text("default_action: allow\nrules: []\n")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = PolicyEngine(tmp_path)
        # default.yaml's "ask" must survive — zzz_last.yaml cannot clobber it
        assert engine.default_action == "ask"
