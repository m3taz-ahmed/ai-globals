#!/usr/bin/env python3
"""Semantic code search (from metis).

Search code by meaning, not just text. Uses TF-IDF-like scoring
on code tokens to find semantically similar functions.

Usage::

    from runtime.semantic_search import SemanticCodeSearch

    search = SemanticCodeSearch()
    search.index_file(Path("module.py"))
    results = search.search("user authentication logic")
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from runtime.codegraph import CodeGraphBuilder, FunctionNode


@dataclass
class SearchResult:
    """A single semantic search result."""

    function: FunctionNode
    score: float
    snippet: str = ""


@dataclass
class SemanticCodeSearch:
    """Semantic code search using TF-IDF-like scoring (from metis).

    Indexes functions by their token frequencies and searches by
    computing similarity scores.
    """

    _functions: list[FunctionNode] = field(default_factory=list)
    _token_freqs: dict[str, dict[str, int]] = field(default_factory=dict)  # func_name → {token: freq}
    _doc_freqs: dict[str, int] = field(default_factory=dict)  # token → num docs containing it
    _sources: dict[str, str] = field(default_factory=dict)  # func_name → source snippet

    def index_file(self, file_path: Path) -> None:
        """Index all functions in a file."""
        builder = CodeGraphBuilder()
        graph = builder.build_from_file(file_path)
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
            lines = source.split("\n")
        except OSError:
            lines = []
        for func in graph.functions:
            self._functions.append(func)
            snippet = "\n".join(lines[func.line - 1:func.end_line]) if lines else ""
            self._sources[func.name] = snippet
            tokens = self._tokenize(snippet)
            freq: dict[str, int] = {}
            for token in tokens:
                freq[token] = freq.get(token, 0) + 1
            self._token_freqs[func.name] = freq
            for token in freq:
                self._doc_freqs[token] = self._doc_freqs.get(token, 0) + 1

    def index_directory(self, directory: Path) -> None:
        """Index all Python files in a directory."""
        for f in directory.rglob("*.py"):
            if any(p in {".git", "__pycache__", ".venv"} for p in f.parts):
                continue
            self.index_file(f)

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for functions matching the query semantically."""
        query_tokens = self._tokenize(query)
        if not query_tokens or not self._functions:
            return []
        total_docs = len(self._functions)
        results: list[SearchResult] = []
        for func in self._functions:
            score = self._score(query_tokens, func.name, total_docs)
            if score > 0:
                results.append(SearchResult(
                    function=func,
                    score=score,
                    snippet=self._sources.get(func.name, "")[:200],
                ))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    def _score(
        self,
        query_tokens: list[str],
        func_name: str,
        total_docs: int,
    ) -> float:
        """Compute TF-IDF similarity score."""
        freq = self._token_freqs.get(func_name, {})
        if not freq:
            return 0.0
        score = 0.0
        for token in query_tokens:
            tf = freq.get(token, 0)
            if tf == 0:
                continue
            df = self._doc_freqs.get(token, 0)
            if df == 0:
                continue
            idf = math.log(total_docs / df) + 1
            score += tf * idf
        # Normalize by function length
        total_tokens = sum(freq.values()) or 1
        return score / math.sqrt(total_tokens)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract meaningful tokens from code text."""
        tokens = re.findall(r"\b\w+\b", text.lower())
        # Filter out very common code tokens
        stop_words = {"def", "return", "self", "cls", "the", "a", "an", "if", "else",
                      "for", "while", "import", "from", "class", "try", "except",
                       "with", "as", "in", "is", "not", "and", "or", "none", "true", "false"}
        return [t for t in tokens if t not in stop_words and len(t) > 1]


if __name__ == "__main__":
    search = SemanticCodeSearch()
    search.index_file(Path(__file__))
    results = search.search("fuzz testing policy")
    for r in results:
        print(f"{r.function.name}: {r.score:.2f}")
