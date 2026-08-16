#!/usr/bin/env python3
"""CodeGraph builder and reachability analysis (from metis).

Language-neutral representation of code symbols, calls, and source
locations. Uses AST parsing (Python) for accurate symbol extraction.
Cross-language support via tree-sitter can be added via plugins.

Usage::

    from runtime.codegraph import CodeGraphBuilder, ReachabilityAnalyzer

    builder = CodeGraphBuilder()
    graph = builder.build_from_file(Path("module.py"))
    analyzer = ReachabilityAnalyzer(graph)
    paths = analyzer.find_paths("func_a", "func_b")
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FunctionNode:
    """A function definition in the code graph."""

    name: str
    file_path: str
    line: int
    end_line: int
    args: list[str] = field(default_factory=list)


@dataclass
class CallEdge:
    """A function call edge in the code graph."""

    caller: str
    callee: str
    file_path: str
    line: int


@dataclass
class CodeGraph:
    """Language-neutral code graph with functions and call edges."""

    functions: list[FunctionNode] = field(default_factory=list)
    calls: list[CallEdge] = field(default_factory=list)
    _func_index: dict[str, FunctionNode] = field(default_factory=dict)
    _call_index: dict[str, list[CallEdge]] = field(default_factory=dict)

    def add_function(self, func: FunctionNode) -> None:
        self.functions.append(func)
        self._func_index[func.name] = func

    def add_call(self, call: CallEdge) -> None:
        self.calls.append(call)
        self._call_index.setdefault(call.caller, []).append(call)

    def get_function(self, name: str) -> FunctionNode | None:
        return self._func_index.get(name)

    def get_calls_from(self, func_name: str) -> list[CallEdge]:
        return self._call_index.get(func_name, [])

    def merge(self, other: CodeGraph) -> None:
        """Merge another graph into this one."""
        for f in other.functions:
            self.add_function(f)
        for c in other.calls:
            self.add_call(c)


class CodeGraphBuilder:
    """Builds a CodeGraph from Python source files using AST."""

    def build_from_file(self, file_path: Path) -> CodeGraph:
        """Build a code graph from a single Python file."""
        graph = CodeGraph()
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, OSError):
            return graph
        self._extract_functions(tree, file_path, graph)
        self._extract_calls(tree, file_path, graph)
        return graph

    def build_from_directory(
        self,
        directory: Path,
        extensions: set[str] | None = None,
    ) -> CodeGraph:
        """Build a code graph from all Python files in a directory."""
        if extensions is None:
            extensions = {".py"}
        graph = CodeGraph()
        for f in directory.rglob("*"):
            if not f.is_file() or f.suffix not in extensions:
                continue
            if any(p in {".git", "__pycache__", ".venv", "node_modules"} for p in f.parts):
                continue
            sub = self.build_from_file(f)
            graph.merge(sub)
        return graph

    def _extract_functions(
        self, tree: ast.AST, file_path: Path, graph: CodeGraph,
    ) -> None:
        """Extract function definitions from AST."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [a.arg for a in node.args.args]
                graph.add_function(FunctionNode(
                    name=node.name,
                    file_path=str(file_path),
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    args=args,
                ))

    def _extract_calls(
        self, tree: ast.AST, file_path: Path, graph: CodeGraph,
    ) -> None:
        """Extract function call edges from AST."""
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                caller = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        callee = self._get_callee_name(child)
                        if callee:
                            graph.add_call(CallEdge(
                                caller=caller,
                                callee=callee,
                                file_path=str(file_path),
                                line=child.lineno,
                            ))

    @staticmethod
    def _get_callee_name(call: ast.Call) -> str | None:
        """Extract the function name from a Call node."""
        func = call.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return None


@dataclass
class ReachabilityAnalyzer:
    """Reachability analysis for code graphs (from metis).

    Finds paths from source to sink functions, with configurable
    max path length to prevent infinite traversal.
    """

    graph: CodeGraph
    max_path_length: int = 25

    def find_paths(self, source: str, sink: str) -> list[list[str]]:
        """Find all paths from source function to sink function."""
        if source == sink:
            return [[source]]
        visited: set[str] = set()
        paths: list[list[str]] = []
        self._dfs(source, sink, [source], visited, paths)
        return paths

    def _dfs(
        self,
        current: str,
        sink: str,
        path: list[str],
        visited: set[str],
        paths: list[list[str]],
    ) -> None:
        if len(path) > self.max_path_length:
            return
        if current == sink:
            paths.append(list(path))
            return
        visited.add(current)
        for edge in self.graph.get_calls_from(current):
            if edge.callee not in visited:
                path.append(edge.callee)
                self._dfs(edge.callee, sink, path, visited, paths)
                path.pop()
        visited.discard(current)

    def is_reachable(self, source: str, sink: str) -> bool:
        """Check if sink is reachable from source."""
        return len(self.find_paths(source, sink)) > 0

    def get_callers(self, func_name: str) -> list[str]:
        """Get all functions that call the given function."""
        callers: list[str] = []
        for edge in self.graph.calls:
            if edge.callee == func_name and edge.caller not in callers:
                callers.append(edge.caller)
        return callers

    def get_callees(self, func_name: str) -> list[str]:
        """Get all functions called by the given function."""
        return [e.callee for e in self.graph.get_calls_from(func_name)]


if __name__ == "__main__":
    builder = CodeGraphBuilder()
    graph = builder.build_from_file(Path(__file__))
    print(f"Functions: {len(graph.functions)}, Calls: {len(graph.calls)}")
