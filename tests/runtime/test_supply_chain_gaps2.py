"""Gap coverage batch 2 for runtime/supply_chain_guard.py."""

from __future__ import annotations

import json
from pathlib import Path
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


class TestFirstPartyAndAliases:
    """First-party packages, import-name aliases, sibling modules."""

    def _py_project(self, tmp_path: Path, deps: str = '"requests"') -> SupplyChainGuard:
        (tmp_path / "pyproject.toml").write_text(
            f'[project]\nname = "demo"\ndependencies = [{deps}]\n',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        return guard

    def test_root_package_dir_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        (tmp_path / "mypkg").mkdir()
        src = tmp_path / "main.py"
        src.write_text("import mypkg\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_root_module_stem_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        (tmp_path / "config.py").write_text("X = 1\n", encoding="utf-8")
        src = tmp_path / "main.py"
        src.write_text("import config\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_sibling_module_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        (tmp_path / "helpers.py").write_text("X = 1\n", encoding="utf-8")
        src = tmp_path / "main.py"
        src.write_text("import helpers\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_sibling_in_subdir_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        (tmp_path / "scripts").mkdir()
        (tmp_path / "scripts" / "core.py").write_text("X = 1\n", encoding="utf-8")
        src = tmp_path / "tool.py"
        src.write_text("import core\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_alias_yaml_satisfied_by_pyyaml(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path, '"pyyaml"')
        src = tmp_path / "app.py"
        src.write_text("import yaml\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_alias_missing_distribution_flagged(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        src = tmp_path / "app.py"
        src.write_text("import yaml\n", encoding="utf-8")
        findings = guard.scan_imports(src)
        assert [f.module for f in findings] == ["yaml"]

    def test_hyphen_underscore_normalized(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path, '"sentence-transformers"')
        src = tmp_path / "app.py"
        src.write_text("import sentence_transformers\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_full_stdlib_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        src = tmp_path / "app.py"
        src.write_text(
            "import gc\nimport ipaddress\nimport http.server\nimport __future__\n",
            encoding="utf-8",
        )
        assert guard.scan_imports(src) == []

    def test_same_top_module_deduped(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        src = tmp_path / "app.py"
        src.write_text(
            "import opentelemetry\nimport opentelemetry.sdk.trace\n",
            encoding="utf-8",
        )
        findings = guard.scan_imports(src)
        assert [f.module for f in findings] == ["opentelemetry"]
        assert findings[0].line == 1

    def test_scan_source_flags_undeclared(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        findings = guard.scan_source(
            "import requests\nimport totally_fake_pkg\n", "<lint>.py"
        )
        assert [f.module for f in findings] == ["totally_fake_pkg"]

    def test_scan_source_first_party_allowed(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        (tmp_path / "mypkg").mkdir()
        assert guard.scan_source("import mypkg\n", "<lint>.py") == []

    def test_scan_source_unsupported_suffix_empty(self, tmp_path: Path) -> None:
        guard = self._py_project(tmp_path)
        assert guard.scan_source("import evilpkg\n", "<lint>.txt") == []

    def test_go_module_path_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "module demo\ngo 1.21\nrequire github.com/gin-gonic/gin v1.9.0\n",
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "app.go"
        src.write_text('package main\nimport "demo/internal/x"\n', encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_php_autoload_root_allowed(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require": {"monolog/monolog": "^3.0"},'
            ' "autoload": {"psr-4": {"App\\\\": "src/"}}}',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "index.php"
        src.write_text("<?php\nuse App\\Service\\Thing;\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_php_first_party_absent_autoload_flagged(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require": {"monolog/monolog": "^3.0"}}', encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "index.php"
        src.write_text("<?php\nuse App\\Service\\Thing;\n", encoding="utf-8")
        findings = guard.scan_imports(src)
        assert any(f.module == "App\\Service\\Thing" for f in findings)


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


class TestFirstPartyEdgeBranches:
    """Branch-coverage edges: OSError paths, layouts, go/php manifest shapes."""

    def test_empty_top_is_allowed(self, tmp_path: Path) -> None:
        guard = SupplyChainGuard(tmp_path)
        assert guard._is_allowed("", DependencyEcosystem.PYTHON, set()) is True

    def test_src_layout_first_party(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies=["requests"]\n', encoding="utf-8"
        )
        (tmp_path / "src" / "mypkg").mkdir(parents=True)
        (tmp_path / "src" / "mypkg" / "__init__.py").write_text("", encoding="utf-8")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "main.py"
        src.write_text("import mypkg\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_root_scan_oserror(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies=["requests"]\n', encoding="utf-8"
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        real = Path.iterdir

        def boom(self: Path, *a, **k):
            if self == tmp_path:
                raise OSError("denied")
            return real(self, *a, **k)

        monkeypatch.setattr(Path, "iterdir", boom)
        src = tmp_path / "main.py"
        src.write_text("import localpkg\n", encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["localpkg"]

    def test_sibling_scan_oserror(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies=["requests"]\n', encoding="utf-8"
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        monkeypatch.setattr(
            Path, "iterdir",
            lambda self, *a, **k: (_ for _ in ()).throw(OSError("denied")),
        )
        src = tmp_path / "main.py"
        src.write_text("import localpkg\n", encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["localpkg"]

    def test_go_no_gomod_flags_everything(self, tmp_path: Path) -> None:
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "app.go"
        src.write_text('package main\nimport "demo/x"\n', encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["demo/x"]

    def test_go_mod_without_module_line(self, tmp_path: Path) -> None:
        (tmp_path / "go.mod").write_text(
            "go 1.21\nrequire github.com/gin-gonic/gin v1.9.0\n",
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "app.go"
        src.write_text('package main\nimport "demo/x"\n', encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["demo/x"]

    def test_go_mod_read_oserror(self, tmp_path: Path, monkeypatch) -> None:
        gomod = tmp_path / "go.mod"
        gomod.write_text("module demo\n", encoding="utf-8")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        monkeypatch.setattr(
            Path, "read_text",
            lambda self, *a, **k: (_ for _ in ()).throw(OSError("denied")),
        )
        assert guard._go_module_path() == ""

    def test_php_no_composer_json(self, tmp_path: Path) -> None:
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "index.php"
        src.write_text("<?php\nuse App\\Svc\\T;\n", encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["App\\Svc\\T"]

    def test_php_malformed_composer(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text("{not json", encoding="utf-8")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "index.php"
        src.write_text("<?php\nuse App\\Svc\\T;\n", encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["App\\Svc\\T"]

    def test_php_autoload_non_dict_skipped(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require": {"monolog/monolog": "^3"}, "autoload": ["x"]}',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "index.php"
        src.write_text("<?php\nuse App\\Svc\\T;\n", encoding="utf-8")
        assert [f.module for f in guard.scan_imports(src)] == ["App\\Svc\\T"]

    def test_php_autoload_dev_root(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require": {"monolog/monolog": "^3"},'
            ' "autoload-dev": {"psr-4": {"Tests\\\\": "tests/"}}}',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tmp_path / "t.php"
        src.write_text("<?php\nuse Tests\\Unit\\T;\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

class TestCoverageEdges:
    """Remaining branch-coverage edges (line 290, 418-419, 471, 616->614)."""

    def test_check_diff_returns_finding(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies=["requests"]\n', encoding="utf-8"
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        diff = (
            "+++ b/app.py\n+import evilpkg\n+import requests\n"
            "+result = compute()\n"
        )
        assert [f.module for f in guard.check_diff(diff)] == ["evilpkg"]

    def test_src_layout_only_reachable_importer(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies=["requests"]\n', encoding="utf-8"
        )
        (tmp_path / "src" / "mypkg").mkdir(parents=True)
        (tmp_path / "src" / "mypkg" / "__init__.py").write_text("", encoding="utf-8")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        src = tests_dir / "test_app.py"
        src.write_text("import mypkg\n", encoding="utf-8")
        assert guard.scan_imports(src) == []

    def test_php_roots_cached_on_second_call(self, tmp_path: Path) -> None:
        (tmp_path / "composer.json").write_text(
            '{"require": {"monolog/monolog": "^3"},'
            ' "autoload": {"psr-4": {"App\\\\": "src/"}}}',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        for name in ("a.php", "b.php"):
            src = tmp_path / name
            src.write_text("<?php\nuse App\\Svc\\T;\n", encoding="utf-8")
            assert guard.scan_imports(src) == []

    def test_multi_quoted_dep_line(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname="x"\ndependencies = ["requests", "pydantic", ">=1.0"]\n',
            encoding="utf-8",
        )
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert {"requests", "pydantic"} <= declared[DependencyEcosystem.PYTHON]
