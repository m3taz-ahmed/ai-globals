"""Tests for runtime/codegraph.py — CodeGraph builder and reachability."""

from __future__ import annotations

from pathlib import Path

from runtime.codegraph import CodeGraphBuilder, ReachabilityAnalyzer

SAMPLE_CODE = '''
def func_a():
    func_b()
    func_c()

def func_b():
    func_c()

def func_c():
    pass

def func_d():
    func_a()
'''


class TestCodeGraphBuilder:
    def test_build_from_file(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        assert len(graph.functions) == 4
        names = [f.name for f in graph.functions]
        assert "func_a" in names
        assert "func_b" in names

    def test_extract_call_edges(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        calls_from_a = graph.get_calls_from("func_a")
        callees = [c.callee for c in calls_from_a]
        assert "func_b" in callees
        assert "func_c" in callees

    def test_build_from_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text("def foo(): bar()", encoding="utf-8")
        (tmp_path / "b.py").write_text("def bar(): pass", encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_directory(tmp_path)
        assert len(graph.functions) >= 2

    def test_syntax_error_handled(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.py"
        f.write_text("def broken(:", encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        assert len(graph.functions) == 0


class TestReachabilityAnalyzer:
    def test_find_direct_path(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        analyzer = ReachabilityAnalyzer(graph)
        paths = analyzer.find_paths("func_a", "func_c")
        assert len(paths) > 0
        assert "func_c" in paths[0]

    def test_is_reachable(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        analyzer = ReachabilityAnalyzer(graph)
        assert analyzer.is_reachable("func_d", "func_c") is True

    def test_not_reachable(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        analyzer = ReachabilityAnalyzer(graph)
        assert analyzer.is_reachable("func_c", "func_a") is False

    def test_get_callers(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        analyzer = ReachabilityAnalyzer(graph)
        callers = analyzer.get_callers("func_c")
        assert "func_a" in callers
        assert "func_b" in callers

    def test_get_callees(self, tmp_path: Path) -> None:
        f = tmp_path / "sample.py"
        f.write_text(SAMPLE_CODE, encoding="utf-8")
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(f)
        analyzer = ReachabilityAnalyzer(graph)
        callees = analyzer.get_callees("func_a")
        assert "func_b" in callees
