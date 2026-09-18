"""Tests for runtime/hallucination_detector.py — hallucinated import detection."""

from __future__ import annotations

import tempfile
from pathlib import Path

from runtime.hallucination_detector import (
    HallucinationDetector,
    HallucinationSeverity,
)


class TestPython:
    def test_known_stdlib(self):
        d = HallucinationDetector()
        code = "import os\nimport json\nfrom pathlib import Path\nfrom typing import Any"
        assert d.detect_python(code) == []

    def test_known_pypi(self):
        d = HallucinationDetector()
        code = "import numpy as np\nfrom pydantic import BaseModel\nimport pytest"
        assert d.detect_python(code) == []

    def test_hallucinated_import(self):
        d = HallucinationDetector()
        f = d.detect_python("import definitely_not_real_pkg_xyz", "f.py")
        assert len(f) == 1
        assert f[0].package_name == "definitely_not_real_pkg_xyz"
        assert f[0].severity is HallucinationSeverity.HIGH
        assert f[0].file_path == "f.py"
        assert f[0].line_number == 1

    def test_hallucinated_from_import(self):
        d = HallucinationDetector()
        f = d.detect_python("from fakepkg.sub import Thing", "f.py")
        assert len(f) == 1
        assert f[0].package_name == "fakepkg"
        assert "from fakepkg.sub import Thing" in f[0].import_statement

    def test_mixed(self):
        d = HallucinationDetector()
        code = "import os\nimport fake_lib_99\nimport sys"
        f = d.detect_python(code)
        assert len(f) == 1 and f[0].line_number == 2

    def test_syntax_error_skipped(self):
        d = HallucinationDetector()
        assert d.detect_python("def broken(:") == []

    def test_relative_import_skipped(self):
        d = HallucinationDetector()
        # `from . import x` — node.module is None
        assert d.detect_python("from . import helper") == []

    def test_multiline(self):
        d = HallucinationDetector()
        code = "x = 1\n\n\nimport imaginary_pkg\n"
        f = d.detect_python(code)
        assert f[0].line_number == 4


class TestJavaScript:
    def test_known_packages(self):
        d = HallucinationDetector()
        code = "import React from 'react';\nimport { z } from 'zod';\nconst _ = require('lodash');"
        assert d.detect_javascript(code) == []

    def test_scoped_packages(self):
        d = HallucinationDetector()
        code = "import x from '@tanstack/react-query';"
        assert d.detect_javascript(code) == []

    def test_unknown_scoped(self):
        d = HallucinationDetector()
        code = "import x from '@fakecorp/secret-pkg';"
        f = d.detect_javascript(code)
        assert len(f) == 1 and f[0].package_name == "@fakecorp/secret-pkg"

    def test_relative_imports_ignored(self):
        d = HallucinationDetector()
        code = "import { helper } from './utils';\nimport x from '../lib/mod';"
        assert d.detect_javascript(code) == []

    def test_require_unknown(self):
        d = HallucinationDetector()
        f = d.detect_javascript("const x = require('made_up_pkg');")
        assert len(f) == 1 and f[0].package_name == "made_up_pkg"

    def test_type_only_import(self):
        d = HallucinationDetector()
        f = d.detect_javascript("import type { T } from 'not_a_pkg';")
        assert len(f) == 1

    def test_side_effect_import(self):
        d = HallucinationDetector()
        f = d.detect_javascript("import 'polyfill-fake';")
        assert len(f) == 1


class TestTypeScript:
    def test_ts_detection(self):
        d = HallucinationDetector()
        f = d.detect_typescript("import { fake } from 'notrealpkg';", "x.ts")
        assert len(f) == 1 and f[0].language == "typescript"

    def test_known_ts_pkg(self):
        d = HallucinationDetector()
        assert d.detect_typescript("import { defineConfig } from 'vite';") == []


class TestScanFile:
    def test_py_file(self):
        d = HallucinationDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.py"
            p.write_text("import fake_pkg_42\n")
            f = d.scan_file(p)
            assert len(f) == 1

    def test_ts_file(self):
        d = HallucinationDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.ts"
            p.write_text("import x from 'unrealpkg';\n")
            f = d.scan_file(p)
            assert len(f) == 1 and f[0].language == "typescript"

    def test_unsupported_ext(self):
        d = HallucinationDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.rs"
            p.write_text("use fake;\n")
            assert d.scan_file(p) == []

    def test_scan_directory(self):
        d = HallucinationDetector()
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.py").write_text("import fake_a\n")
            Path(td, "b.js").write_text("import x from 'fake_b';\n")
            Path(td, "c.txt").write_text("nothing")
            f = d.scan_directory(Path(td))
            assert len(f) == 2

    def test_scan_directory_limit(self):
        d = HallucinationDetector()
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                Path(td, f"f{i}.py").write_text("import x\n")
            f = d.scan_directory(Path(td), max_files=2)
            assert len(f) <= 2


class TestFinding:
    def test_to_dict(self):
        d = HallucinationDetector()
        f = d.detect_python("import nonexistent123")[0]
        dd = f.to_dict()
        assert dd["package_name"] == "nonexistent123"
        assert dd["severity"] == "high"
        assert "not in the known package registry" in dd["reason"]
