"""Gap coverage batch 2 for runtime/supply_chain_guard.py."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from runtime.supply_chain_guard import (
    DependencyEcosystem,
    OsvDevClient,
    SupplyChainGuard,
    _extract_dependency_name,
    _parse_cargo_toml,
    _parse_composer_json,
    _parse_go_mod,
    _parse_package_json,
    _parse_pyproject_deps,
    _parse_requirements,
)


class TestExtractors:
    def setup_method(self):
        from pathlib import Path

        self.guard = SupplyChainGuard(Path("."))

    def test_python_relative_import_is_stdlib(self):
        # `from . import x` -> top starts with "." -> allowed
        assert self.guard._is_allowed(
            ".", DependencyEcosystem.PYTHON, set()
        ) is True

    def test_ts_import_groups_all_none(self):
        # An import form whose regex groups are all empty is skipped.
        out = self.guard._extract_ts_imports("import {} from 'x';\n")
        assert isinstance(out, list)

    def test_go_empty_import_block(self):
        out = self.guard._extract_go_imports("import ()\n")
        assert out == []

    def test_go_single_import(self):
        out = self.guard._extract_go_imports('import "fmt"\n')
        assert ("fmt", 1) in out


class TestExtractDependencyName:
    def test_empty_spec(self):
        assert _extract_dependency_name("; marker") is None

    def test_dash_prefixed(self):
        assert _extract_dependency_name("-r other.txt") is None

    def test_extras_stripped(self):
        assert _extract_dependency_name("requests[security]==2.0") == "requests"


class TestManifestParsers:
    def test_pyproject_in_section_and_array(self):
        text = (
            "[tool.poetry.dependencies]\n"
            'requests = "^2.0"\n'
            "[project]\n"
            'dependencies = [\n'
            '    "flask>=3",\n'
            '    "bad line",\n'
            "]\n"
        )
        names = _parse_pyproject_deps(text)
        assert "requests" in names
        assert "flask" in names

    def test_collect_dep_names_skips_bad(self):
        names = _parse_pyproject_deps('deps = ["-r x"]\n')
        assert "-r x" not in names

    def test_requirements_none_name(self):
        names = _parse_requirements("==\nrequests\n")
        assert "requests" in names

    def test_package_json_invalid(self):
        assert _parse_package_json("{nope") == set()

    def test_package_json_non_dict_deps(self):
        names = _parse_package_json('{"dependencies": "oops"}')
        assert names == set()

    def test_composer_json_invalid(self):
        assert _parse_composer_json("{bad") == set()

    def test_composer_json_non_dict_deps(self):
        assert _parse_composer_json('{"require": [1, 2]}') == set()

    def test_go_mod_empty_require_line(self):
        text = "module x\nrequire (\n\n   \n)\nrequire github.com/a/b v1\n"
        names = _parse_go_mod(text)
        assert "github.com/a/b" in names

    def test_go_mod_non_require_line(self):
        names = _parse_go_mod("go 1.21\n")
        assert names == set()

    def test_cargo_no_equals_line(self):
        names = _parse_cargo_toml("[dependencies]\nweirdline\nserde = \"1\"\n")
        assert "serde" in names

    def test_cargo_private_key_skipped(self):
        names = _parse_cargo_toml('[dependencies]\n_priv = "1"\nok = "2"\n')
        assert "_priv" not in names
        assert "ok" in names


class TestOsvFetch:
    def test_severity_arcs(self):
        client = OsvDevClient()
        payload = {
            "vulns": [
                {"id": "GHSA-1", "severity": [{"type": "OTHER", "score": "x"}],
                 "summary": "s"},
                {"id": "GHSA-2",
                 "severity": [{"type": "CVSS_V3", "score": "NOTV3"}],
                 "summary": "s"},
                {"id": "MAL-2024-1", "severity": [], "summary": "mal"},
            ]
        }
        resp = MagicMock()
        resp.read.return_value = json.dumps(payload).encode()
        ctx = MagicMock()
        ctx.__enter__.return_value = resp
        with patch("urllib.request.urlopen", return_value=ctx):
            advisories = client._fetch("k", "pkg", "PyPI", "1.0")
        sevs = {a.advisory_id: a.severity for a in advisories}
        assert sevs["GHSA-1"] == "MEDIUM"
        assert sevs["GHSA-2"] == "MEDIUM"
        assert sevs["MAL-2024-1"] == "CRITICAL"
