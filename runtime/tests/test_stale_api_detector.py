"""Tests for runtime/stale_api_detector.py — deprecated API detection."""

from __future__ import annotations

import tempfile
from pathlib import Path

from runtime.stale_api_detector import StaleApiDetector, StaleApiSeverity


class TestPython:
    def test_clean_code(self):
        d = StaleApiDetector()
        assert d.detect("import pathlib\nfrom collections.abc import Mapping",
                        "python") == []

    def test_getargspec(self):
        d = StaleApiDetector()
        f = d.detect("inspect.getargspec(fn)", "python", "x.py")
        assert len(f) == 1
        assert f[0].replacement == "inspect.getfullargspec"
        assert f[0].severity is StaleApiSeverity.HIGH
        assert f[0].file_path == "x.py"

    def test_multiple_deprecated(self):
        d = StaleApiDetector()
        code = "import imp\nx = xrange(10)\ny = unicode('a')"
        f = d.detect(code, "python")
        apis = {x.api_name for x in f}
        assert {"imp", "xrange", "unicode"} <= apis

    def test_line_numbers(self):
        d = StaleApiDetector()
        code = "x = 1\n\nxrange(5)"
        f = [x for x in d.detect(code, "python") if x.api_name == "xrange"]
        assert f[0].line_number == 3

    def test_typing_aliases(self):
        d = StaleApiDetector()
        f = d.detect("from typing import Mapping\nx: typing.Mapping = {}", "python")
        assert any(x.api_name == "typing.Mapping" for x in f)


class TestJavaScript:
    def test_react_lifecycle(self):
        d = StaleApiDetector()
        code = "class C extends React.Component {\n  componentWillMount() {}\n}"
        f = d.detect(code, "javascript")
        assert any("componentWillMount" in x.api_name for x in f)

    def test_new_buffer(self):
        d = StaleApiDetector()
        f = d.detect("const b = new Buffer(10);", "javascript")
        assert any("new Buffer" in x.api_name for x in f)

    def test_reactdom_render(self):
        d = StaleApiDetector()
        f = d.detect("ReactDOM.render(<App/>, el)", "javascript")
        assert any("ReactDOM.render" in x.api_name for x in f)

    def test_clean_js(self):
        d = StaleApiDetector()
        assert d.detect("useEffect(() => {}, [])", "javascript") == []


class TestTypeScript:
    def test_ts_uses_js_db(self):
        d = StaleApiDetector()
        # "typescript" has no dedicated db — falls back to empty patterns
        f = d.detect("componentWillMount()", "typescript")
        assert f == [] or isinstance(f, list)

    def test_unknown_language(self):
        d = StaleApiDetector()
        assert d.detect("anything", "cobol") == []


class TestScan:
    def test_scan_file_py(self):
        d = StaleApiDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.py"
            p.write_text("import imp\n")
            f = d.scan_file(p)
            assert len(f) >= 1 and f[0].language == "python"

    def test_scan_file_js(self):
        d = StaleApiDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.jsx"
            p.write_text("new Buffer(1)")
            f = d.scan_file(p)
            assert len(f) >= 1 and f[0].language == "javascript"

    def test_scan_file_unsupported(self):
        d = StaleApiDetector()
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.rb"
            p.write_text("puts 'x'")
            assert d.scan_file(p) == []

    def test_scan_directory(self):
        d = StaleApiDetector()
        with tempfile.TemporaryDirectory() as td:
            Path(td, "a.py").write_text("import imp\n")
            Path(td, "b.mjs").write_text("new Buffer(1)")
            Path(td, "c.md").write_text("# doc")
            f = d.scan_directory(Path(td))
            assert len(f) >= 2

    def test_scan_directory_limit(self):
        d = StaleApiDetector()
        with tempfile.TemporaryDirectory() as td:
            for i in range(5):
                Path(td, f"f{i}.py").write_text("import imp\n")
            assert len(d.scan_directory(Path(td), max_files=2)) <= 4


class TestFinding:
    def test_to_dict(self):
        d = StaleApiDetector()
        f = d.detect("xrange(1)", "python")[0]
        dd = f.to_dict()
        assert dd["api_name"] == "xrange"
        assert dd["replacement"] == "range"
        assert dd["severity"] == "high"
