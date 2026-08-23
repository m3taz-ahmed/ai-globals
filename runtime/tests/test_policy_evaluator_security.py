"""Security regression tests for the policy condition evaluator.

These lock down a critical privilege-escalation bug: YAML-style ``true``
literals in conditions were parsed as variable names, so ``flag == true``
matched every action MISSING that flag (None == None -> True).
"""

from __future__ import annotations

from runtime.policy import PolicyEngine, _SafeEvaluator


class TestYamlLiteralResolution:
    """`true`/`false`/`null` must resolve as literals, not missing variables."""

    def test_eq_true_missing_attr_does_not_match(self) -> None:
        ev = _SafeEvaluator({"type": "edit"})
        assert ev.evaluate("reversible == true") is False

    def test_eq_true_present_attr_matches(self) -> None:
        ev = _SafeEvaluator({"type": "edit", "reversible": True})
        assert ev.evaluate("reversible == true") is True

    def test_eq_false_missing_attr_does_not_match(self) -> None:
        # Previously: None == None -> True. Must be False.
        ev = _SafeEvaluator({"type": "edit"})
        assert ev.evaluate("dry_run == false") is False

    def test_eq_false_present_attr_matches(self) -> None:
        ev = _SafeEvaluator({"type": "edit", "dry_run": False})
        assert ev.evaluate("dry_run == false") is True

    def test_ne_true_with_missing_attr_matches(self) -> None:
        # force_push(None) != true(True) -> True
        ev = _SafeEvaluator({"command": "git push"})
        assert ev.evaluate("force_push != true") is True

    def test_null_literal(self) -> None:
        ev = _SafeEvaluator({"token": None})
        assert ev.evaluate("token == null") is True

    def test_python_capitalized_bools_still_work(self) -> None:
        ev = _SafeEvaluator({"reversible": True})
        assert ev.evaluate("reversible == True") is True


class TestMembershipOnMissingAttributes:
    """`'x' in missing_attr` must not match (and must not warn/crash)."""

    def test_in_on_missing_returns_false(self) -> None:
        ev = _SafeEvaluator({"type": "ChatMessage"})
        assert ev.evaluate("'git commit' in command") is False

    def test_not_in_on_missing_is_fail_closed(self) -> None:
        # Unevaluable comparisons must NOT match rules (fail-closed):
        # 'git commit' not in <missing> -> TypeError -> False.
        ev = _SafeEvaluator({})
        assert ev.evaluate("'git commit' not in command") is False

    def test_or_chain_with_missing_command_no_warning_path(self) -> None:
        ev = _SafeEvaluator({"type": "ChatMessage"})
        assert ev.evaluate(
            "'git commit' in command or 'git push' in command or 'git reset --hard' in command or force_push == true"
        ) is False


class TestPolicyEngineEndToEnd:
    """Full-engine regression for the consequence-tiers scenario."""

    def _engine_with_git_rule(self, tmp_path) -> PolicyEngine:
        policies = tmp_path / "runtime" / "policies"
        policies.mkdir(parents=True)
        (policies / "default.yaml").write_text("default_action: ask\nrules: []\n", encoding="utf-8")
        (policies / "tiers.yaml").write_text(
            "rules:\n"
            "  - name: git-writes-deny\n"
            "    condition: \"'git commit' in command or force_push == true\"\n"
            "    action: deny\n",
            encoding="utf-8",
        )
        return PolicyEngine(tmp_path)

    def test_chat_message_not_denied_by_git_rule(self, tmp_path) -> None:
        engine = self._engine_with_git_rule(tmp_path)
        d = engine.can("ChatMessage", content="what is the status?", approved=True)
        assert d["decision"] != "deny"

    def test_real_git_commit_still_denied(self, tmp_path) -> None:
        engine = self._engine_with_git_rule(tmp_path)
        d = engine.can("Bash", command="git commit -m x")
        assert d["decision"] == "deny"

    def test_force_push_flag_still_denied(self, tmp_path) -> None:
        engine = self._engine_with_git_rule(tmp_path)
        d = engine.can("Bash", command="git push", force_push=True)
        assert d["decision"] == "deny"

    def test_reversible_allow_rule_scoped_correctly(self, tmp_path) -> None:
        policies = tmp_path / "runtime" / "policies"
        policies.mkdir(parents=True)
        (policies / "default.yaml").write_text("default_action: ask\nrules: []\n", encoding="utf-8")
        (policies / "delegated.yaml").write_text(
            "rules:\n"
            "  - name: delegated-reversible-writes\n"
            "    condition: \"type in ['edit', 'write', 'apply'] and reversible == true\"\n"
            "    action: allow\n",
            encoding="utf-8",
        )
        engine = PolicyEngine(tmp_path)
        # Missing reversible flag: must NOT auto-allow (was the escalation hole).
        d = engine.can("write", path="f.txt")
        assert d["decision"] != "allow"
        # Explicitly reversible write: allowed.
        d2 = engine.can("write", path="f.txt", reversible=True)
        assert d2["decision"] == "allow"
