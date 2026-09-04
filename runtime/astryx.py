#!/usr/bin/env python3
"""AST-based code review for AI-generated Python.

Re-implements the astryx pattern: run lightweight static analysis rules over
Python source without executing it.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LintFinding:
    """A single lint finding."""

    rule: str
    line: int
    message: str
    severity: str = "warning"


class _AstryxVisitor(ast.NodeVisitor):
    """AST visitor that collects findings."""

    def __init__(self, max_lines: int = 50, max_params: int = 7) -> None:
        self.findings: list[LintFinding] = []
        self._max_lines = max_lines
        self._max_params = max_params

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_function(node)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self._add("no-bare-except", node, "Avoid bare except clauses")
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self._add("no-broad-except", node, "Avoid broad except Exception clauses")
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if node.end_lineno and node.body and getattr(node.body[0], "lineno", None):
            body_lines = node.end_lineno - node.body[0].lineno + 1
        else:
            body_lines = node.end_lineno - (node.lineno or 1) + 1 if node.end_lineno else 0
        if body_lines > self._max_lines:
            self._add(
                "function-too-long",
                node,
                f"Function has {body_lines} lines (limit {self._max_lines})",
            )
        params = len(node.args.args) + len(node.args.kwonlyargs)
        # *args/**kwargs count as 0 extra (unbounded, not fixed arity).
        if params > self._max_params:
            self._add("too-many-params", node, f"Function has {params} parameters (limit {self._max_params})")
        for default in node.args.defaults + node.args.kw_defaults:
            if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self._add("no-mutable-default", default, "Avoid mutable default arguments", severity="error")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self._add("no-eval", node, f"Avoid {node.func.id}()", severity="error")
        self.generic_visit(node)

    def _add(self, rule: str, node: ast.AST, message: str, severity: str = "warning") -> None:
        line = getattr(node, "lineno", 0) or 0
        self.findings.append(LintFinding(rule=rule, line=line, message=message, severity=severity))


class AstryxLinter:
    """Linter entry point."""

    def __init__(self, max_lines: int = 50, max_params: int = 7) -> None:
        self._max_lines = max_lines
        self._max_params = max_params

    def lint(self, source: str | Path) -> list[LintFinding]:
        if isinstance(source, Path):
            try:
                text = source.read_text(encoding="utf-8")
            except (IsADirectoryError, OSError) as exc:
                return [LintFinding(rule="file-read-error", line=0, message=f"{exc!s}", severity="error")]
        else:
            text = source
        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            return [LintFinding(rule="syntax-error", line=exc.lineno or 0, message=f"{exc!s}", severity="error")]
        visitor = _AstryxVisitor(max_lines=self._max_lines, max_params=self._max_params)
        visitor.visit(tree)
        return visitor.findings

    def lint_text(self, text: str) -> list[LintFinding]:
        return self.lint(text)


def format_findings(findings: list[LintFinding]) -> str:
    """Render findings as a human-friendly string."""
    if not findings:
        return "No findings."
    lines = []
    for finding in findings:
        lines.append(f"{finding.severity}: {finding.rule} at line {finding.line}: {finding.message}")
    return "\n".join(lines)
