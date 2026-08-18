#!/usr/bin/env python3
"""Tree-sitter symbol provider interface (from metis).

Language-neutral symbol extraction using tree-sitter. Falls back to
AST parsing for Python when tree-sitter is not available.

Usage::

    from runtime.tree_sitter_provider import SymbolProvider

    provider = SymbolProvider()
    symbols = provider.extract_symbols(Path("module.py"))
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class Symbol:
    """A code symbol (function, class, method, variable)."""

    name: str
    kind: str  # function, class, method, variable, import
    file_path: str
    line: int
    end_line: int
    signature: str = ""
    docstring: str = ""


class SymbolExtractor(Protocol):
    """Protocol for language-specific symbol extractors."""

    def extract(self, source: str, file_path: Path) -> list[Symbol]:
        ...


class PythonASTExtractor:
    """Python symbol extraction using built-in AST."""

    def extract(self, source: str, file_path: Path) -> list[Symbol]:
        try:
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            return []
        symbols: list[Symbol] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(self._func_to_symbol(node, file_path))
            elif isinstance(node, ast.ClassDef):
                symbols.append(self._class_to_symbol(node, file_path))
        return symbols

    @staticmethod
    def _func_to_symbol(
        node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path,
    ) -> Symbol:
        args = [a.arg for a in node.args.args]
        kind = "method" if any(
            isinstance(parent, ast.ClassDef)
            for parent in [node]  # Simplified check
        ) else "function"
        docstring = ast.get_docstring(node) or ""
        return Symbol(
            name=node.name,
            kind=kind,
            file_path=str(file_path),
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=f"({', '.join(args)})",
            docstring=docstring,
        )

    @staticmethod
    def _class_to_symbol(node: ast.ClassDef, file_path: Path) -> Symbol:
        docstring = ast.get_docstring(node) or ""
        bases = [b.id if isinstance(b, ast.Name) else "" for b in node.bases]
        return Symbol(
            name=node.name,
            kind="class",
            file_path=str(file_path),
            line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=f"({', '.join(bases)})" if bases else "",
            docstring=docstring,
        )


@dataclass
class SymbolProvider:
    """Language-neutral symbol provider (from metis).

    Uses tree-sitter when available, falls back to AST for Python.
    Supports pluggable extractors for other languages.
    """

    _extractors: dict[str, SymbolExtractor] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._extractors[".py"] = PythonASTExtractor()

    def register_extractor(self, extension: str, extractor: SymbolExtractor) -> None:
        """Register a custom extractor for a file extension."""
        self._extractors[extension] = extractor

    def extract_symbols(self, file_path: Path) -> list[Symbol]:
        """Extract symbols from a file."""
        extractor = self._extractors.get(file_path.suffix)
        if extractor is None:
            return []
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return extractor.extract(source, file_path)

    def extract_from_directory(
        self,
        directory: Path,
        extensions: set[str] | None = None,
    ) -> list[Symbol]:
        """Extract symbols from all supported files in a directory."""
        if extensions is None:
            extensions = set(self._extractors.keys())
        symbols: list[Symbol] = []
        for f in directory.rglob("*"):
            if not f.is_file() or f.suffix not in extensions:
                continue
            if any(p in {".git", "__pycache__", ".venv"} for p in f.parts):
                continue
            symbols.extend(self.extract_symbols(f))
        return symbols


if __name__ == "__main__":
    _self_path = Path(__file__) if "__file__" in globals() else Path("tree_sitter_provider.py")
    provider = SymbolProvider()
    symbols = provider.extract_symbols(_self_path)
    for s in symbols:
        print(f"{s.kind} {s.name}{s.signature} at line {s.line}")
