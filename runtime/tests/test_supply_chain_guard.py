"""Tests for runtime/supply_chain_guard.py — undeclared import detection."""

from __future__ import annotations

import textwrap
from pathlib import Path

from runtime.supply_chain_guard import (
    DeclaredDependency,
    DependencyEcosystem,
    SupplyChainGuard,
    UndeclaredImport,
)


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _make_project(tmp_path: Path) -> Path:
    """Create a project root with python/node/php/go manifests."""
    _write(
        tmp_path / "pyproject.toml",
        textwrap.dedent(
            """
            [project]
            name = "demo"
            dependencies = ["requests>=2.0", "rich"]
            """
        ).strip(),
    )
    _write(
        tmp_path / "package.json",
        '{"dependencies": {"express": "^4.0", "lodash": "^4.17"},'
        ' "devDependencies": {"jest": "^29.0"}}',
    )
    _write(
        tmp_path / "composer.json",
        '{"require": {"monolog/monolog": "^3.0"},'
        ' "require-dev": {"phpunit/phpunit": "^10.0"}}',
    )
    _write(
        tmp_path / "go.mod",
        textwrap.dedent(
            """
            module demo
            go 1.21
            require (
                github.com/gin-gonic/gin v1.9.0
            )
            require github.com/stretchr/testify v1.8.0
            """
        ).strip(),
    )
    return tmp_path


class TestDependencyEcosystem:
    def test_python_value(self) -> None:
        assert DependencyEcosystem.PYTHON.value == "python"

    def test_node_value(self) -> None:
        assert DependencyEcosystem.NODE.value == "node"

    def test_php_value(self) -> None:
        assert DependencyEcosystem.PHP.value == "php"

    def test_go_value(self) -> None:
        assert DependencyEcosystem.GO.value == "go"

    def test_is_str_enum(self) -> None:
        assert isinstance(DependencyEcosystem.PYTHON, str)


class TestDeclaredDependency:
    def test_fields(self) -> None:
        dep = DeclaredDependency("requests", "2.0", DependencyEcosystem.PYTHON)
        assert dep.name == "requests"
        assert dep.version == "2.0"
        assert dep.ecosystem == DependencyEcosystem.PYTHON


class TestUndeclaredImport:
    def test_default_line_zero(self) -> None:
        finding = UndeclaredImport("newpkg", "f.py", DependencyEcosystem.PYTHON)
        assert finding.line == 0

    def test_fields(self) -> None:
        finding = UndeclaredImport("newpkg", "f.py", DependencyEcosystem.PYTHON, 5)
        assert finding.module == "newpkg"
        assert finding.file == "f.py"
        assert finding.ecosystem == DependencyEcosystem.PYTHON
        assert finding.line == 5


class TestLoadDeclared:
    def test_python_from_pyproject(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert "requests" in declared[DependencyEcosystem.PYTHON]
        assert "rich" in declared[DependencyEcosystem.PYTHON]

    def test_node_from_package_json(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert "express" in declared[DependencyEcosystem.NODE]
        assert "lodash" in declared[DependencyEcosystem.NODE]
        assert "jest" in declared[DependencyEcosystem.NODE]

    def test_php_from_composer(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert "monolog/monolog" in declared[DependencyEcosystem.PHP]
        assert "phpunit/phpunit" in declared[DependencyEcosystem.PHP]

    def test_go_from_go_mod(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert "github.com/gin-gonic/gin" in declared[DependencyEcosystem.GO]
        assert "github.com/stretchr/testify" in declared[DependencyEcosystem.GO]

    def test_empty_project_returns_empty_sets(self, tmp_path: Path) -> None:
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert declared[DependencyEcosystem.PYTHON] == set()
        assert declared[DependencyEcosystem.NODE] == set()

    def test_requirements_txt_parsed(self, tmp_path: Path) -> None:
        _write(tmp_path / "requirements.txt", "requests>=2.0\n# comment\nflask==2.0\n")
        guard = SupplyChainGuard(tmp_path)
        declared = guard.load_declared()
        assert "requests" in declared[DependencyEcosystem.PYTHON]
        assert "flask" in declared[DependencyEcosystem.PYTHON]


class TestScanImportsPython:
    def test_declared_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.py",
            "import requests\nimport os\nfrom rich import print\n",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        modules = [f.module for f in findings]
        assert "requests" not in modules
        assert "rich" not in modules

    def test_undeclared_import_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.py",
            "import requests\nimport brand_new_pkg\n",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        modules = [f.module for f in findings]
        assert "brand_new_pkg" in modules

    def test_stdlib_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.py",
            "import os\nimport sys\nimport json\nimport pathlib\n",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []

    def test_from_import_undeclared_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.py",
            "from undeclared_pkg import something\n",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert any(f.module == "undeclared_pkg" for f in findings)

    def test_line_number_captured(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.py",
            "import os\nimport requests\nimport brand_new_pkg\n",
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        brand = next(f for f in findings if f.module == "brand_new_pkg")
        assert brand.line == 3

    def test_relative_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.py", "from . import helpers\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []


class TestScanImportsTs:
    def test_declared_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.ts", "import express from 'express';\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []

    def test_undeclared_import_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.ts", "import leftpad from 'leftpad';\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert any(f.module == "leftpad" for f in findings)

    def test_relative_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.ts", "import { x } from './helpers';\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []

    def test_require_undeclared_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.js", "const x = require('leftpad');\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert any(f.module == "leftpad" for f in findings)


class TestScanImportsPhp:
    def test_declared_use_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.php", "<?php\nuse Monolog\\Logger;\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []

    def test_undeclared_use_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.php", "<?php\nuse Some\\Undeclared;\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert any(f.module == "Some\\Undeclared" for f in findings)


class TestScanImportsGo:
    def test_declared_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.go",
            'package main\nimport "github.com/gin-gonic/gin"\n',
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []

    def test_undeclared_import_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.go",
            'package main\nimport "github.com/fake/pkg"\n',
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert any(f.module == "github.com/fake/pkg" for f in findings)

    def test_import_block_multiple(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "app.go",
            textwrap.dedent(
                """
                package main
                import (
                    "github.com/gin-gonic/gin"
                    "github.com/fake/pkg"
                )
                """
            ).strip(),
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        modules = [f.module for f in findings]
        assert "github.com/gin-gonic/gin" not in modules
        assert "github.com/fake/pkg" in modules


class TestCheckDiff:
    def test_added_python_import_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        diff = textwrap.dedent(
            """
            diff --git a/app.py b/app.py
            --- a/app.py
            +++ b/app.py
            @@ -1,1 +1,2 @@
             import os
            +import brand_new_pkg
            """
        ).strip()
        findings = guard.check_diff(diff)
        assert any(f.module == "brand_new_pkg" for f in findings)

    def test_declared_added_import_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        diff = textwrap.dedent(
            """
            diff --git a/app.py b/app.py
            +++ b/app.py
            @@ -1,1 +1,2 @@
             import os
            +import requests
            """
        ).strip()
        findings = guard.check_diff(diff)
        assert findings == []

    def test_removed_lines_not_checked(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        diff = textwrap.dedent(
            """
            diff --git a/app.py b/app.py
            +++ b/app.py
            @@ -1,2 +1,1 @@
            -import brand_new_pkg
             import os
            """
        ).strip()
        findings = guard.check_diff(diff)
        assert findings == []

    def test_added_ts_import_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        diff = textwrap.dedent(
            """
            diff --git a/app.ts b/app.ts
            +++ b/app.ts
            @@ -1,1 +1,2 @@
             import express from 'express';
            +import leftpad from 'leftpad';
            """
        ).strip()
        findings = guard.check_diff(diff)
        assert any(f.module == "leftpad" for f in findings)


class TestCheckFile:
    def test_check_file_alias_scan_imports(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(tmp_path / "app.py", "import brand_new_pkg\n")
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        assert guard.check_file(src) == guard.scan_imports(src)


class TestStdlibExclusion:
    def test_comprehensive_stdlib_not_flagged(self, tmp_path: Path) -> None:
        _make_project(tmp_path)
        src = _write(
            tmp_path / "stdlib.py",
            textwrap.dedent(
                """
                import os, sys, re, json, pathlib, typing, dataclasses, enum
                import collections, functools, ast, threading, hashlib, datetime
                import abc, io, csv, math, itertools, warnings, contextlib
                import urllib, logging, time, copy, inspect, unittest
                import configparser, sqlite3, xml, html, base64, uuid, secrets
                import hmac, ssl, socket, select, signal, struct, codecs
                import locale, pprint, textwrap, shutil, tempfile, subprocess
                import platform, getpass, argparse
                """
            ).strip(),
        )
        guard = SupplyChainGuard(tmp_path)
        guard.load_declared()
        findings = guard.scan_imports(src)
        assert findings == []
