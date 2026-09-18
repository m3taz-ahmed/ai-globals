"""Gap coverage for supply_chain_guard: rust/cargo, typosquat, OSV client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from runtime.schemas import ValidationError
from runtime.supply_chain_guard import (
    DependencyEcosystem,
    OsvDevClient,
    SupplyChainGuard,
    SupplyChainGuardError,
    TyposquatDetector,
    _levenshtein,
    _parse_cargo_toml,
)


class TestCargoRust:
    def test_cargo_deps(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[dependencies]\nserde = "1.0"\ntokio = { version = "1" }\n'
            "[dev-dependencies]\nanyhow = \"1\"\n[other]\nx = 1\n"
        )
        names = _parse_cargo_toml((tmp_path / "Cargo.toml").read_text())
        assert {"serde", "tokio", "anyhow"} <= names

    def test_rust_use_declared(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[dependencies]\nserde = "1"\n')
        (tmp_path / "main.rs").write_text("use serde::Serialize;\nuse std::io;\n")
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "main.rs") == []

    def test_rust_undeclared(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text('[dependencies]\nserde = "1"\n')
        (tmp_path / "main.rs").write_text("use evilcrate::x;\nuse crate::y;\n")
        g = SupplyChainGuard(tmp_path)
        findings = g.scan_imports(tmp_path / "main.rs")
        assert len(findings) == 1 and findings[0].module == "evilcrate"

    def test_rust_in_diff_not_supported(self, tmp_path):
        g = SupplyChainGuard(tmp_path)
        findings = g.check_diff("+++ b/main.rs\n+use evilcrate;\n")
        assert findings == []


class TestGuardEdges:
    def test_missing_file(self, tmp_path):
        g = SupplyChainGuard(tmp_path)
        with pytest.raises(ValidationError):
            g.scan_imports(tmp_path / "nope.py")

    def test_unknown_suffix(self, tmp_path):
        (tmp_path / "x.txt").write_text("import evilpkg")
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "x.txt") == []

    def test_syntax_error_py(self, tmp_path):
        (tmp_path / "bad.py").write_text("def broken(:\n")
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "bad.py") == []

    def test_huge_py_skipped(self, tmp_path):
        src = "import os\n" + ("# pad\n" * (11 * 1024 * 1024 // 6))
        g = SupplyChainGuard(tmp_path)
        assert g._extract_python_imports(src) == []

    def test_diff_no_plus_b_header(self, tmp_path):
        g = SupplyChainGuard(tmp_path)
        findings = g.check_diff("+++ x.py\n+import evilpkg\n")
        assert any(f.module == "evilpkg" for f in findings)

    def test_diff_before_header_ignored(self, tmp_path):
        g = SupplyChainGuard(tmp_path)
        assert g.check_diff("+import evilpkg\n") == []

    def test_diff_php(self, tmp_path):
        (tmp_path / "composer.json").write_text(
            json.dumps({"require": {"laravel/framework": "^10"}}))
        g = SupplyChainGuard(tmp_path)
        findings = g.check_diff("+++ b/x.php\n+use Evil\\Hack;\n")
        assert len(findings) == 1

    def test_diff_go(self, tmp_path):
        g = SupplyChainGuard(tmp_path)
        findings = g.check_diff('+++ b/x.go\n+import "evil/mod"\n')
        assert len(findings) == 1

    def test_php_case_insensitive_vendor(self, tmp_path):
        (tmp_path / "composer.json").write_text(
            json.dumps({"require": {"laravel/framework": "^10"}}))
        (tmp_path / "x.php").write_text("use Laravel\\Http\\Request;\n")
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "x.php") == []

    def test_node_scoped_pkg(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"@scope/pkg": "1.0"}}))
        (tmp_path / "x.ts").write_text('import x from "@scope/pkg/sub";\n')
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "x.ts") == []

    def test_node_builtin(self, tmp_path):
        (tmp_path / "x.ts").write_text('import fs from "node:fs";\n')
        g = SupplyChainGuard(tmp_path)
        assert g.scan_imports(tmp_path / "x.ts") == []

    def test_go_undeclared(self, tmp_path):
        (tmp_path / "x.go").write_text('import "evil.io/x"\n')
        g = SupplyChainGuard(tmp_path)
        findings = g.scan_imports(tmp_path / "x.go")
        assert len(findings) == 1


class TestTyposquat:
    def test_exact_legit(self):
        d = TyposquatDetector()
        assert d.check("requests", DependencyEcosystem.PYTHON) == []

    def test_edit_distance(self):
        d = TyposquatDetector()
        findings = d.check("reqeusts", DependencyEcosystem.PYTHON)
        assert any(f.suspected_of == "requests" and f.reason == "edit_distance"
                   for f in findings)

    def test_homoglyph(self):
        d = TyposquatDetector()
        # 'flask' -> 'fIask' (l -> I homoglyph); distance 1 also triggers
        findings = d.check("fIask", DependencyEcosystem.PYTHON)
        assert findings and findings[0].suspected_of == "flask"

    def test_homoglyph_only(self):
        d = TyposquatDetector(threshold=0)
        findings = d.check("fIask", DependencyEcosystem.PYTHON)
        assert findings and findings[0].reason == "homoglyph"

    def test_unrelated(self):
        d = TyposquatDetector()
        assert d.check("totally-unique-pkg-xyz", DependencyEcosystem.PYTHON) == []

    def test_node_ecosystem(self):
        d = TyposquatDetector()
        findings = d.check("reac", DependencyEcosystem.NODE)
        assert any(f.suspected_of == "react" for f in findings)

    def test_unknown_ecosystem(self):
        d = TyposquatDetector()
        assert d.check("anything", DependencyEcosystem.GO) == []

    def test_custom_popular(self):
        d = TyposquatDetector(popular_python={"mypkg"}, popular_node=set())
        findings = d.check("mypkgx", DependencyEcosystem.PYTHON)
        assert findings and findings[0].suspected_of == "mypkg"

    def test_levenshtein_empty(self):
        assert _levenshtein("abc", "") == 3
        assert _levenshtein("", "abc") == 3
        assert _levenshtein("a", "a") == 0

    def test_homoglyph_len_mismatch(self):
        assert not TyposquatDetector._has_homoglyph_match("aa", "aaa")


class TestOsvClient:
    def _resp(self, vulns):
        m = MagicMock()
        m.read.return_value = json.dumps({"vulns": vulns}).encode()
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        return m

    def test_query_vulns(self):
        c = OsvDevClient()
        vulns = [{"id": "GHSA-x", "summary": "bad",
                  "severity": [{"type": "CVSS_V3", "score": "CVSS:3.1/x"}]}]
        with patch("urllib.request.urlopen", return_value=self._resp(vulns)):
            out = c.query("pkg", DependencyEcosystem.PYTHON, "1.0")
        assert out[0].advisory_id == "GHSA-x" and out[0].severity == "HIGH"

    def test_mal_critical(self):
        c = OsvDevClient()
        vulns = [{"id": "MAL-2024-1", "summary": "malware"}]
        with patch("urllib.request.urlopen", return_value=self._resp(vulns)):
            out = c.query("pkg", DependencyEcosystem.NODE)
        assert out[0].severity == "CRITICAL"

    def test_default_medium(self):
        c = OsvDevClient()
        with patch("urllib.request.urlopen", return_value=self._resp([{"id": "X"}])):
            out = c.query("pkg", DependencyEcosystem.PHP)
        assert out[0].severity == "MEDIUM"

    def test_cache_hit(self):
        c = OsvDevClient()
        c._cache["PyPI:pkg:1.0"] = (__import__("time").time(), ["cached"])  # type: ignore[list-item]
        assert c.query("pkg", DependencyEcosystem.PYTHON, "1.0") == ["cached"]

    def test_network_fail_closed(self):
        import urllib.error

        c = OsvDevClient()
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("down")):
            with pytest.raises(SupplyChainGuardError):
                c.query("pkg", DependencyEcosystem.PYTHON)

    def test_bad_json_fail_closed(self):
        c = OsvDevClient()
        m = MagicMock()
        m.read.return_value = b"{bad"
        m.__enter__ = lambda s: s
        m.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=m):
            with pytest.raises(SupplyChainGuardError):
                c.query("pkg", DependencyEcosystem.PYTHON)

    def test_ecosystem_maps(self):
        assert OsvDevClient._ecosystem_str(DependencyEcosystem.NODE) == "npm"
        assert OsvDevClient._ecosystem_str(DependencyEcosystem.GO) == "Go"
        assert OsvDevClient._ecosystem_str(DependencyEcosystem.RUST) == "PyPI"
        assert OsvDevClient._str_to_ecosystem("npm") == DependencyEcosystem.NODE
        assert OsvDevClient._str_to_ecosystem("other") == DependencyEcosystem.PYTHON
