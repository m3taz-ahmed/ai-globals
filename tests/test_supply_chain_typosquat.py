"""Tests for runtime.supply_chain_guard — typosquat + OSV.dev (from AgentGuard)."""

from __future__ import annotations

from runtime.supply_chain_guard import (
    DependencyEcosystem,
    OsvDevClient,
    TyposquatDetector,
    _levenshtein,
)


def test_levenshtein_identical() -> None:
    assert _levenshtein("hello", "hello") == 0


def test_levenshtein_one_char() -> None:
    assert _levenshtein("hello", "hallo") == 1


def test_levenshtein_empty() -> None:
    assert _levenshtein("", "abc") == 3


def test_typosquat_exact_match_no_finding() -> None:
    det = TyposquatDetector()
    findings = det.check("requests", DependencyEcosystem.PYTHON)
    assert len(findings) == 0


def test_typosquat_close_match_detected() -> None:
    det = TyposquatDetector(threshold=2)
    findings = det.check("reqeusts", DependencyEcosystem.PYTHON)  # transposition
    assert len(findings) > 0
    assert findings[0].suspected_of == "requests"
    assert findings[0].reason == "edit_distance"


def test_typosquat_homoglyph_detected() -> None:
    det = TyposquatDetector(threshold=2)
    # "nurnpy" — rn looks like m, edit distance 2 from "numpy"
    findings = det.check("nurnpy", DependencyEcosystem.PYTHON)
    # Should be detected via edit_distance (distance=2)
    assert len(findings) > 0
    assert findings[0].suspected_of == "numpy"


def test_typosquat_far_match_not_detected() -> None:
    det = TyposquatDetector(threshold=2)
    findings = det.check("completely_different", DependencyEcosystem.PYTHON)
    assert len(findings) == 0


def test_typosquat_node_ecosystem() -> None:
    det = TyposquatDetector(threshold=2)
    findings = det.check("reqeusts", DependencyEcosystem.NODE)
    # "requests" is not in the default Node popular list, so no match
    # Let's test with "reack" → "react"
    findings = det.check("reack", DependencyEcosystem.NODE)
    assert len(findings) > 0
    assert findings[0].suspected_of == "react"


def test_osv_dev_client_caches_results() -> None:
    client = OsvDevClient(cache_ttl=60)
    # Mock the _fetch method to avoid network calls
    call_count = 0

    def mock_fetch(cache_key, package, eco_str, version):
        nonlocal call_count
        call_count += 1
        return []

    client._fetch = mock_fetch  # type: ignore
    client.query("test-pkg", DependencyEcosystem.PYTHON)
    client.query("test-pkg", DependencyEcosystem.PYTHON)  # Should use cache
    assert call_count == 1


def test_osv_dev_client_ecosystem_str() -> None:
    assert OsvDevClient._ecosystem_str(DependencyEcosystem.PYTHON) == "PyPI"
    assert OsvDevClient._ecosystem_str(DependencyEcosystem.NODE) == "npm"
    assert OsvDevClient._ecosystem_str(DependencyEcosystem.PHP) == "Packagist"
    assert OsvDevClient._ecosystem_str(DependencyEcosystem.GO) == "Go"
