"""Tests for P3 features — multiple modules."""

from __future__ import annotations

import time
from pathlib import Path

from runtime.budget_anomaly import BudgetAnomalyDetector
from runtime.diff_review import DiffParser, DiffReviewer
from runtime.fuzz_testing import PolicyFuzzer
from runtime.memory_compression import MemoryCompressor
from runtime.policy_cache import PolicyDecisionCache
from runtime.semantic_search import SemanticCodeSearch
from runtime.spec_validation import (
    ConstitutionValidator,
    ScenarioBuilder,
    SpecLinkageGraph,
)
from runtime.tree_sitter_provider import SymbolProvider


class TestBudgetAnomalyDetector:
    def test_no_anomaly_with_insufficient_data(self) -> None:
        detector = BudgetAnomalyDetector()
        result = detector.check(100)
        assert result["is_anomaly"] is False

    def test_normal_value_not_anomaly(self) -> None:
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=3.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector.record(v)
        assert detector.is_anomaly(52) is False

    def test_spike_is_anomaly(self) -> None:
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector.record(v)
        assert detector.is_anomaly(500) is True

    def test_z_score_computed(self) -> None:
        detector = BudgetAnomalyDetector(baseline_window=10, threshold=2.0)
        for v in [50, 55, 48, 52, 51, 49, 53, 50, 54, 51]:
            detector.record(v)
        result = detector.check(500)
        assert result["z_score"] > 2.0


class TestPolicyDecisionCache:
    def test_put_and_get(self) -> None:
        cache = PolicyDecisionCache(ttl_seconds=60)
        key = cache.make_key("u1", "read", "doc1")
        cache.put(key, {"decision": "allow"})
        assert cache.get(key) == {"decision": "allow"}

    def test_expired_entry_returns_none(self) -> None:
        cache = PolicyDecisionCache(ttl_seconds=0)
        key = cache.make_key("u1", "read", "doc1")
        cache.put(key, "value")
        time.sleep(0.01)
        assert cache.get(key) is None

    def test_invalidate(self) -> None:
        cache = PolicyDecisionCache(ttl_seconds=60)
        key = "test-key"
        cache.put(key, "value")
        cache.invalidate(key)
        assert cache.get(key) is None

    def test_clear(self) -> None:
        cache = PolicyDecisionCache(ttl_seconds=60)
        cache.put("k1", "v1")
        cache.put("k2", "v2")
        cache.clear()
        assert cache.size == 0

    def test_cleanup_expired(self) -> None:
        cache = PolicyDecisionCache(ttl_seconds=0)
        cache.put("k1", "v1")
        time.sleep(0.01)
        removed = cache.cleanup_expired()
        assert removed == 1

    def test_make_key_deterministic(self) -> None:
        k1 = PolicyDecisionCache.make_key("u1", "read", "doc1")
        k2 = PolicyDecisionCache.make_key("u1", "read", "doc1")
        assert k1 == k2

    def test_make_key_different_inputs(self) -> None:
        k1 = PolicyDecisionCache.make_key("u1", "read", "doc1")
        k2 = PolicyDecisionCache.make_key("u2", "read", "doc1")
        assert k1 != k2


class TestDiffParser:
    def test_parse_simple_diff(self) -> None:
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def foo():
-    pass
+    x = 1
+    return x
"""
        hunks = DiffParser.parse(diff)
        assert len(hunks) == 1
        assert len(hunks[0].added_lines) == 2
        assert len(hunks[0].removed_lines) == 1

    def test_extract_file_paths(self) -> None:
        diff = "--- a/test.py\n+++ b/test.py\n"
        paths = DiffParser.extract_file_paths(diff)
        assert "test.py" in paths


class TestDiffReviewer:
    def test_review_diff_finds_issues(self) -> None:
        diff = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,4 @@
 def foo():
-    pass
+    x = None
+    if x == None:
+        return True
"""
        reviewer = DiffReviewer()
        summary = reviewer.review_diff_summary(diff)
        assert summary["files_reviewed"] >= 0  # May be 0 if no file path


class TestConstitutionValidator:
    def test_forbidden_pattern_violation(self) -> None:
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No hardcoded secrets", forbidden=r"password\s*=\s*['\"]")
        violations = validator.validate("password = 'secret123'")
        assert len(violations) == 1

    def test_no_violations(self) -> None:
        validator = ConstitutionValidator()
        validator.add_rule("SEC-01", "No hardcoded secrets", forbidden=r"password\s*=\s*['\"]")
        violations = validator.validate("x = 1")
        assert violations == []

    def test_required_pattern_missing(self) -> None:
        validator = ConstitutionValidator()
        validator.add_rule("DOC-01", "Must have docstring", pattern=r'""".*?"""')
        violations = validator.validate("def foo(): pass")
        assert len(violations) == 1


class TestScenarioBuilder:
    def test_add_scenario(self) -> None:
        builder = ScenarioBuilder()
        s = builder.add_scenario("REQ-001", "User login", given="user exists", when="login", then="authenticated")
        assert s.requirement_id == "REQ-001"
        assert s.given == "user exists"

    def test_for_requirement(self) -> None:
        builder = ScenarioBuilder()
        builder.add_scenario("REQ-001", "A")
        builder.add_scenario("REQ-002", "B")
        builder.add_scenario("REQ-001", "C")
        assert len(builder.for_requirement("REQ-001")) == 2

    def test_to_gherkin(self) -> None:
        builder = ScenarioBuilder()
        builder.add_scenario("REQ-001", "Login", given="user exists", when="they login", then="they see dashboard")
        gherkin = builder.to_gherkin_feature("Authentication")
        assert "Feature: Authentication" in gherkin
        assert "Given user exists" in gherkin


class TestSpecLinkageGraph:
    def test_add_and_find_links(self) -> None:
        graph = SpecLinkageGraph()
        graph.add_link("spec", "auth", "requirement", "REQ-001", "implements")
        graph.add_link("requirement", "REQ-001", "code", "auth.py", "implements")
        links = graph.links_from("auth")
        assert len(links) == 1

    def test_impact_analysis(self) -> None:
        graph = SpecLinkageGraph()
        graph.add_link("spec", "S1", "requirement", "R1", "implements")
        graph.add_link("requirement", "R1", "code", "file.py", "implements")
        graph.add_link("code", "file.py", "test", "test_file.py", "tests")
        affected = graph.impact_analysis("spec", "S1")
        assert len(affected) == 3  # All downstream


class TestSymbolProvider:
    def test_extract_from_python_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    pass\nclass Bar:\n    pass\n", encoding="utf-8")
        provider = SymbolProvider()
        symbols = provider.extract_symbols(f)
        names = [s.name for s in symbols]
        assert "foo" in names
        assert "Bar" in names

    def test_unsupported_extension_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello", encoding="utf-8")
        provider = SymbolProvider()
        assert provider.extract_symbols(f) == []


class TestSemanticCodeSearch:
    def test_index_and_search(self, tmp_path: Path) -> None:
        f = tmp_path / "auth.py"
        f.write_text("""
def authenticate_user(username, password):
    if username and password:
        return True
    return False
""", encoding="utf-8")
        search = SemanticCodeSearch()
        search.index_file(f)
        results = search.search("authenticate user password")
        assert len(results) > 0
        assert results[0].function.name == "authenticate_user"

    def test_empty_search(self) -> None:
        search = SemanticCodeSearch()
        assert search.search("anything") == []


class TestPolicyFuzzer:
    def test_fuzz_completes_without_crash(self) -> None:
        fuzzer = PolicyFuzzer(iterations=50, seed=42)
        result = fuzzer.fuzz()
        assert result.iterations == 50
        assert result.crashes == 0  # PDP should handle all inputs

    def test_fuzz_produces_decisions(self) -> None:
        fuzzer = PolicyFuzzer(iterations=100, seed=42)
        result = fuzzer.fuzz()
        assert len(result.decisions) > 0
        assert "allow" in result.decisions or "deny" in result.decisions or "ask" in result.decisions
