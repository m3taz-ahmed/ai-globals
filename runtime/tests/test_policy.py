"""Comprehensive tests for runtime/policy.py."""

from __future__ import annotations

import warnings
from pathlib import Path

from runtime.policy import PolicyEngine, _SafeEvaluator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_default(root: Path, extra_rules: str = "") -> Path:
    policy_dir = root / "runtime" / "policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
    content = (
        "default_action: ask\nrules:\n"
        "  - name: allow-read\n    condition: \"type == 'Read'\"\n    action: allow\n"
        "  - name: deny-destructive\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
        "  - name: ask-write\n    condition: \"type in ['edit', 'write']\"\n    action: ask\n"
        + extra_rules
    )
    (policy_dir / "default.yaml").write_text(content)
    return root


def _engine(root: Path) -> PolicyEngine:
    return PolicyEngine(root)


# ---------------------------------------------------------------------------
# Basic evaluation
# ---------------------------------------------------------------------------

class TestPolicyEvaluation:
    def test_allow_read(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        assert e.can("Read")["decision"] == "allow"

    def test_deny_destructive(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        assert e.can("rm", command="rm -rf /")["decision"] == "deny"

    def test_ask_write(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        assert e.can("edit")["decision"] == "ask"
        assert e.can("write")["decision"] == "ask"

    def test_default_action_for_unknown(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        result = e.can("deploy")
        assert result["decision"] == "ask"
        assert result["rule"] == "default"
        assert result["requires_approval"] is True

    def test_requires_approval_on_ask(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        result = e.can("edit")
        assert result["requires_approval"] is True

    def test_not_requires_approval_on_allow(self, tmp_path: Path):
        e = _engine(_write_default(tmp_path))
        result = e.can("Read")
        assert result["requires_approval"] is False


# ---------------------------------------------------------------------------
# Multi-file loading
# ---------------------------------------------------------------------------

class TestMultiFileLoading:
    def test_second_yaml_file_rules_are_loaded(self, tmp_path: Path):
        _write_default(tmp_path)
        extra = (
            "rules:\n"
            "  - name: deny-drop\n    condition: \"'DROP TABLE' in query\"\n    action: deny\n"
        )
        (tmp_path / "runtime" / "policies" / "extra.yaml").write_text(extra)
        e = _engine(tmp_path)
        result = e.can("sql", query="DROP TABLE users")
        assert result["decision"] == "deny"
        assert result["rule"] == "deny-drop"

    def test_second_yaml_overrides_default_action(self, tmp_path: Path):
        _write_default(tmp_path)
        extra = "default_action: deny\nrules: []\n"
        (tmp_path / "runtime" / "policies" / "zz-override.yaml").write_text(extra)
        e = _engine(tmp_path)
        # default.yaml sets "ask"; zz-override.yaml (loaded after) sets "deny"
        assert e.default_action == "deny"

    def test_no_policies_dir_loads_cleanly(self, tmp_path: Path):
        e = PolicyEngine(tmp_path)  # no policies dir at all
        assert e.rules == []
        assert e.default_action == "ask"


# ---------------------------------------------------------------------------
# Malformed rule skipping
# ---------------------------------------------------------------------------

class TestMalformedRuleSkipping:
    def test_non_dict_rule_is_skipped(self, tmp_path: Path):
        policy_dir = tmp_path / "runtime" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        (policy_dir / "default.yaml").write_text(
            "default_action: allow\nrules:\n"
            "  - just a string rule\n"
            "  - name: valid\n    condition: \"type == 'Read'\"\n    action: allow\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            e = PolicyEngine(tmp_path)
        assert any("Invalid rule" in str(warning.message) for warning in w)
        assert len(e.rules) == 1
        assert e.rules[0].name == "valid"

    def test_missing_keys_rule_is_skipped(self, tmp_path: Path):
        policy_dir = tmp_path / "runtime" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        (policy_dir / "default.yaml").write_text(
            "default_action: allow\nrules:\n"
            "  - name: broken\n    action: allow\n"  # missing 'condition'
            "  - name: ok\n    condition: \"type == 'X'\"\n    action: deny\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            e = PolicyEngine(tmp_path)
        assert any("malformed" in str(warning.message).lower() for warning in w)
        assert len(e.rules) == 1
        assert e.rules[0].name == "ok"

    def test_invalid_action_rule_is_skipped(self, tmp_path: Path):
        policy_dir = tmp_path / "runtime" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        (policy_dir / "default.yaml").write_text(
            "default_action: allow\nrules:\n"
            "  - name: bad-action\n    condition: \"type == 'X'\"\n    action: execute\n"
            "  - name: good\n    condition: \"type == 'Y'\"\n    action: deny\n"
        )
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            e = PolicyEngine(tmp_path)
        assert any("invalid action" in str(warning.message).lower() for warning in w)
        assert len(e.rules) == 1
        assert e.rules[0].name == "good"

    def test_approvers_and_description_populated(self, tmp_path: Path):
        policy_dir = tmp_path / "runtime" / "policies"
        policy_dir.mkdir(parents=True, exist_ok=True)
        (policy_dir / "default.yaml").write_text(
            "default_action: ask\nrules:\n"
            "  - name: guarded\n    condition: \"type == 'deploy'\"\n    action: ask\n"
            "    description: Needs review\n    approvers: [alice, bob]\n"
        )
        e = PolicyEngine(tmp_path)
        result = e.can("deploy")
        assert result["description"] == "Needs review"
        assert result["approvers"] == ["alice", "bob"]


# ---------------------------------------------------------------------------
# _SafeEvaluator AST node coverage
# ---------------------------------------------------------------------------

class TestSafeEvaluatorNodes:
    def _eval(self, expr: str, ctx: dict | None = None) -> bool:
        return _SafeEvaluator(ctx or {}).evaluate(expr)

    def test_constant_true(self):
        assert self._eval("True") is True

    def test_constant_false(self):
        assert self._eval("False") is False

    def test_list_literal(self):
        assert self._eval("1 in [1, 2, 3]") is True

    def test_tuple_literal(self):
        assert self._eval("'x' in ('x', 'y')") is True

    def test_set_literal(self):
        assert self._eval("'a' in {'a', 'b', 'c'}") is True

    def test_binop_string_concat(self):
        # BinOp Add: "foo" + "bar" == "foobar"
        assert self._eval("'foo' + 'bar' == 'foobar'") is True

    def test_subscript_success(self):
        assert self._eval("meta['key'] == 42", {"meta": {"key": 42}}) is True

    def test_subscript_missing_key(self):
        assert self._eval("meta['missing'] == 'x'", {"meta": {}}) is False

    def test_subscript_on_none(self):
        assert self._eval("nothing['key'] == 'x'", {}) is False

    def test_bool_and(self):
        assert self._eval("True and True") is True
        assert self._eval("True and False") is False

    def test_bool_or(self):
        assert self._eval("False or True") is True
        assert self._eval("False or False") is False

    def test_bool_not(self):
        assert self._eval("not False") is True
        assert self._eval("not True") is False

    def test_comparison_lt(self):
        assert self._eval("cost < 10", {"cost": 5}) is True

    def test_comparison_lte(self):
        assert self._eval("cost <= 5", {"cost": 5}) is True

    def test_comparison_gt(self):
        assert self._eval("cost > 3", {"cost": 5}) is True

    def test_comparison_gte(self):
        assert self._eval("cost >= 5", {"cost": 5}) is True

    def test_comparison_neq(self):
        assert self._eval("type != 'Read'", {"type": "Write"}) is True

    def test_not_in_operator(self):
        assert self._eval("'x' not in ['a', 'b']") is True

    def test_unsupported_compare_op_returns_false(self):
        """Cover line 85: op = None → return False (e.g., FloorDiv is not in _allowed_ops)."""
        import ast
        ev = _SafeEvaluator({})
        # Construct a Compare node with FloorDiv (unsupported as comparison op)
        # which will hit the `if op is None: return False` branch
        expr = ast.parse("1 < 2", mode="eval")
        compare = expr.body
        # Replace the op with an unsupported one
        compare.ops = [ast.FloorDiv()]  # type: ignore[assignment]
        assert ev.visit(compare) is False

    def test_unsupported_node_returns_false(self):
        # Lambda is not supported; evaluate should return False
        assert self._eval("lambda x: x") is False

    def test_no_code_execution(self, tmp_path: Path):
        """__import__ must not execute."""
        e = _engine(_write_default(tmp_path))
        e.rules[0].condition = "__import__('os').system('echo pwned')"
        result = e.can("Read")
        assert result["decision"] == "ask"  # falls through to default

