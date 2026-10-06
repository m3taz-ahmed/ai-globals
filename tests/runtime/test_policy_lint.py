"""Tests for runtime/policy_lint.py — static analysis over policy rules."""

from __future__ import annotations

from runtime.policy_lint import LintSeverity, PolicyLinter


def _lint(rules):
    return PolicyLinter().lint(rules)


def _ids(findings):
    return [f.rule_id for f in findings]


class TestDuplicateIds:
    def test_duplicate_flagged(self):
        f = _lint([{"name": "r1"}, {"name": "r1"}])
        assert "PL001" in _ids(f)
        pl = next(x for x in f if x.rule_id == "PL001")
        assert pl.severity is LintSeverity.ERROR
        assert "first at index 0" in pl.message

    def test_unique_ok(self):
        f = _lint([{"name": "a", "owasp": "LLM01"}, {"name": "b", "owasp": "LLM02"}])
        assert "PL001" not in _ids(f)

    def test_default_names(self):
        f = _lint([{}, {}])  # both get rule_0/rule_1 — no dup
        assert "PL001" not in _ids(f)


class TestUnmatchable:
    def test_contradiction_flagged(self):
        f = _lint([{"name": "r", "condition": "action.type == 'read' and action.type == 'write'"}])
        assert "PL002" in _ids(f)
        assert f[0].severity is LintSeverity.ERROR

    def test_consistent_ok(self):
        f = _lint([{"name": "r", "condition": "action.type == 'read'", "owasp": "x"}])
        assert "PL002" not in _ids(f)

    def test_different_fields_ok(self):
        f = _lint([{"name": "r", "condition": "a == '1' and b == '2'", "owasp": "x"}])
        assert "PL002" not in _ids(f)


class TestRedos:
    def test_nested_quantifier(self):
        f = _lint([{"name": "r", "condition": "matches_pattern: '(a+)+$'"}])
        assert "PL003" in _ids(f)
        assert f[0].severity is LintSeverity.WARNING

    def test_safe_regex(self):
        f = _lint([{"name": "r", "condition": "matches_pattern: '[a-z]+'", "owasp": "x"}])
        assert "PL003" not in _ids(f)

    def test_regex_key(self):
        f = _lint([{"name": "r", "condition": "regex: '(x*)*'"}])
        assert "PL003" in _ids(f)


class TestShadowedDenies:
    def test_deny_after_allow(self):
        rules = [
            {"name": "allow", "action": "allow", "condition": "x == 1"},
            {"name": "deny", "action": "deny", "condition": "x == 1"},
        ]
        f = _lint(rules)
        assert "PL004" in _ids(f)
        assert f[0].severity is LintSeverity.ERROR

    def test_deny_before_allow_ok(self):
        rules = [
            {"name": "deny", "action": "deny", "condition": "x == 1"},
            {"name": "allow", "action": "allow", "condition": "x == 1"},
        ]
        assert "PL004" not in _ids(_lint(rules))

    def test_different_condition_ok(self):
        rules = [
            {"name": "allow", "action": "allow", "condition": "x == 1"},
            {"name": "deny", "action": "deny", "condition": "y == 2"},
        ]
        assert "PL004" not in _ids(_lint(rules))


class TestMissingOwasp:
    def test_missing_flagged(self):
        f = _lint([{"name": "r", "condition": "x == 1"}])
        assert "PL005" in _ids(f)
        assert f[0].severity is LintSeverity.INFO

    def test_owasp_field_ok(self):
        f = _lint([{"name": "r", "condition": "x == 1", "owasp": "LLM01"}])
        assert "PL005" not in _ids(f)

    def test_owasp_mapping_key(self):
        f = _lint([{"name": "r", "condition": "x == 1", "owasp_mapping": "LLM01"}])
        assert "PL005" not in _ids(f)

    def test_metadata_owasp(self):
        f = _lint([{"name": "r", "condition": "x == 1", "metadata": {"owasp": "LLM06"}}])
        assert "PL005" not in _ids(f)


class TestUnreachable:
    def test_after_catchall(self):
        rules = [
            {"name": "catch", "condition": "true"},
            {"name": "never", "condition": "x == 1"},
        ]
        f = _lint(rules)
        assert "PL006" in _ids(f)
        pl = next(x for x in f if x.rule_id == "PL006")
        assert "catch-all" in pl.message

    def test_before_catchall_ok(self):
        rules = [
            {"name": "first", "condition": "x == 1"},
            {"name": "catch", "condition": "true"},
        ]
        assert "PL006" not in _ids(_lint(rules))

    def test_empty_condition_is_catchall(self):
        rules = [{"name": "c", "condition": ""}, {"name": "n", "condition": "x"}]
        assert "PL006" in _ids(_lint(rules))

    def test_star_and_default_catchall(self):
        for cond in ("*", "default", "True", "1"):
            rules = [{"name": "c", "condition": cond}, {"name": "n", "condition": "x==1"}]
            assert "PL006" in _ids(_lint(rules)), cond


class TestEmptyConditions:
    def test_empty_flagged(self):
        f = _lint([{"name": "r", "condition": "", "owasp": "x"}])
        assert "PL007" in _ids(f)

    def test_true_flagged(self):
        f = _lint([{"name": "r", "condition": "true", "owasp": "x"}])
        assert "PL007" in _ids(f)

    def test_specific_ok(self):
        f = _lint([{"name": "r", "condition": "x == 1", "owasp": "y"}])
        assert "PL007" not in _ids(f)


class TestSortAndSerialize:
    def test_errors_first(self):
        rules = [
            {"name": "catch", "condition": "true"},          # PL006 trigger + PL007 info
            {"name": "dup", "condition": "x == 1"},
            {"name": "dup", "condition": "x == 1"},          # PL001 error
        ]
        f = _lint(rules)
        assert f[0].severity is LintSeverity.ERROR
        sev_order = [x.severity for x in f]
        assert sev_order == sorted(sev_order, key=lambda s: {LintSeverity.ERROR: 0, LintSeverity.WARNING: 1, LintSeverity.INFO: 2}[s])

    def test_to_dict(self):
        f = _lint([{"name": "r"}, {"name": "r"}])
        d = f[0].to_dict()
        assert d["rule_id"] == "PL001"
        assert d["severity"] == "error"
        assert d["fix"]

    def test_empty_rules(self):
        assert _lint([]) == []
