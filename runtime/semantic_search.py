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
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from runtime.codegraph import CodeGraphBuilder, FunctionNode

if TYPE_CHECKING:
    from memory.vector import VectorStore


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


# ---------------------------------------------------------------------------
# Hybrid Search with Alpha-Blended Fusion (from Weaviate)
#
# Runs keyword (TF-IDF) and vector (semantic) searches in parallel, then
# fuses the results with an alpha-weighted blend.
#   alpha = 1.0 → pure vector search
#   alpha = 0.0 → pure keyword search
#   alpha = 0.5 → balanced hybrid
# ---------------------------------------------------------------------------

# RRF smoothing constant (Weaviate's FusionRanked uses 60).
_RRF_K: int = 60


@dataclass
class HybridSearchResult:
    """A single hybrid search result with per-leg scores and a fused score."""

    function: FunctionNode
    keyword_score: float  # FTS5/keyword score (normalized 0-1)
    vector_score: float  # cosine similarity (0-1)
    hybrid_score: float  # fused score
    snippet: str = ""
    source: str = ""  # "keyword", "vector", "hybrid"


# Module-level backends so hybrid_search() can be called without explicit
# wiring. Tests can replace these via set_hybrid_backends().
_default_keyword_search: SemanticCodeSearch | None = None
_default_vector_store: VectorStore | None = None


def set_hybrid_backends(
    keyword_search: SemanticCodeSearch | None = None,
    vector_store: VectorStore | None = None,
) -> None:
    """Configure the default backends used by hybrid_search()."""
    global _default_keyword_search, _default_vector_store
    _default_keyword_search = keyword_search
    _default_vector_store = vector_store


def _get_keyword_search() -> SemanticCodeSearch:
    if _default_keyword_search is None:
        return SemanticCodeSearch()
    return _default_keyword_search


def _get_vector_store() -> Any:
    return _default_vector_store


def _run_keyword_search(query: str, limit: int) -> list[SearchResult]:
    """Run the keyword (TF-IDF) search leg."""
    search = _get_keyword_search()
    return search.search(query, limit=limit)


def _run_vector_search(
    query_vector: list[float] | None, limit: int,
    filter_metadata: dict[str, Any] | None = None,
) -> list[tuple[str, float]]:
    """Run the vector (semantic) search leg.

    Returns a list of ``(id, score)`` tuples where *id* is the vector
    store id (expected to correspond to a function name).
    """
    store = _get_vector_store()
    if store is None or query_vector is None:
        return []
    results: list[tuple[str, float]] = store.search(
        query_vector, limit=limit, filter_metadata=filter_metadata,
    )
    return results


def hybrid_search(
    query: str,
    query_vector: list[float] | None = None,
    alpha: float = 0.5,
    limit: int = 10,
    filter_metadata: dict[str, Any] | None = None,
) -> list[HybridSearchResult]:
    """Run keyword and vector searches in parallel, then fuse with alpha blend.

    alpha=1.0 → pure vector search
    alpha=0.0 → pure keyword (TF-IDF) search
    alpha=0.5 → balanced hybrid
    """
    over_fetch = limit * 3
    with ThreadPoolExecutor(max_workers=2) as executor:
        keyword_future = executor.submit(_run_keyword_search, query, over_fetch)
        vector_future = executor.submit(
            _run_vector_search, query_vector, over_fetch, filter_metadata,
        )
        keyword_results = keyword_future.result()
        vector_results = vector_future.result()

    # Pure-vector or pure-keyword short-circuits.
    if alpha >= 1.0:
        return _vector_only_results(vector_results, keyword_results, limit)
    if alpha <= 0.0:
        return _keyword_only_results(keyword_results, limit)

    return fuse_relative_score(keyword_results, vector_results, alpha, limit)


def _keyword_only_results(
    keyword_results: list[SearchResult], limit: int,
) -> list[HybridSearchResult]:
    """Build HybridSearchResult list from keyword results only (alpha=0)."""
    fused: list[HybridSearchResult] = []
    for r in keyword_results[:limit]:
        fused.append(HybridSearchResult(
            function=r.function,
            keyword_score=min(r.score, 1.0),
            vector_score=0.0,
            hybrid_score=min(r.score, 1.0),
            snippet=r.snippet,
            source="keyword",
        ))
    return fused


def _vector_only_results(
    vector_results: list[tuple[str, float]],
    keyword_results: list[SearchResult],
    limit: int,
) -> list[HybridSearchResult]:
    """Build HybridSearchResult list from vector results only (alpha=1)."""
    func_lookup = {r.function.name: r for r in keyword_results}
    ks = _get_keyword_search()
    for func in ks._functions:
        if func.name not in func_lookup:
            func_lookup[func.name] = SearchResult(function=func, score=0.0)
    fused: list[HybridSearchResult] = []
    for vid, score in vector_results[:limit]:
        match = func_lookup.get(vid)
        if match is None:
            continue
        fused.append(HybridSearchResult(
            function=match.function,
            keyword_score=0.0,
            vector_score=max(score, 0.0),
            hybrid_score=max(score, 0.0),
            snippet=match.snippet,
            source="vector",
        ))
    return fused


# ---------------------------------------------------------------------------
# Fusion strategies
# ---------------------------------------------------------------------------


def fuse_rrf(
    keyword_results: list[SearchResult],
    vector_results: list[tuple[str, float]],
    alpha: float,
    limit: int,
) -> list[HybridSearchResult]:
    """Reciprocal Rank Fusion: score = weight / (rank + 60).

    RRF is simple and parameter-free. The ``alpha`` weight controls the
    keyword-vs-vector balance (``1-alpha`` for keyword, ``alpha`` for
    vector).
    """
    func_lookup = _build_func_lookup(keyword_results)
    scores: dict[str, float] = {}
    kw_orig: dict[str, float] = {}
    vec_orig: dict[str, float] = {}

    kw_weight = 1.0 - alpha
    vec_weight = alpha

    for rank, r in enumerate(keyword_results):
        name = r.function.name
        scores[name] = scores.get(name, 0.0) + kw_weight / (rank + _RRF_K)
        kw_orig[name] = r.score

    for rank, (vid, vscore) in enumerate(vector_results):
        scores[vid] = scores.get(vid, 0.0) + vec_weight / (rank + _RRF_K)
        vec_orig[vid] = max(vscore, 0.0)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    results: list[HybridSearchResult] = []
    for name, hybrid in ranked[:limit]:
        match = func_lookup.get(name)
        if match is None:
            continue
        results.append(HybridSearchResult(
            function=match.function,
            keyword_score=min(kw_orig.get(name, 0.0), 1.0),
            vector_score=vec_orig.get(name, 0.0),
            hybrid_score=hybrid,
            snippet=match.snippet,
            source=_classify_source(name, kw_orig, vec_orig),
        ))
    return results


def fuse_relative_score(
    keyword_results: list[SearchResult],
    vector_results: list[tuple[str, float]],
    alpha: float,
    limit: int,
) -> list[HybridSearchResult]:
    """Normalize scores to [0,1] then weight-combine.

    More tunable than RRF and better for known score distributions.
    """
    func_lookup = _build_func_lookup(keyword_results)
    kw_norm = _normalize_keyword_scores(keyword_results)
    vec_norm = _normalize_vector_scores(vector_results)

    all_names: set[str] = set(kw_norm) | set(vec_norm)
    combined: list[tuple[str, float, float, float]] = []
    for name in all_names:
        kw = kw_norm.get(name, 0.0)
        vec = vec_norm.get(name, 0.0)
        hybrid = (1.0 - alpha) * kw + alpha * vec
        combined.append((name, kw, vec, hybrid))

    combined.sort(key=lambda x: x[3], reverse=True)

    results: list[HybridSearchResult] = []
    for name, kw, vec, hybrid in combined[:limit]:
        match = func_lookup.get(name)
        if match is None:
            continue
        results.append(HybridSearchResult(
            function=match.function,
            keyword_score=kw,
            vector_score=vec,
            hybrid_score=hybrid,
            snippet=match.snippet,
            source=_classify_source(name, kw_norm, vec_norm),
        ))
    return results


# ---------------------------------------------------------------------------
# Fusion helpers
# ---------------------------------------------------------------------------


def _build_func_lookup(keyword_results: list[SearchResult]) -> dict[str, SearchResult]:
    """Build a name → SearchResult map from keyword results + indexed funcs."""
    lookup = {r.function.name: r for r in keyword_results}
    ks = _get_keyword_search()
    for func in ks._functions:
        if func.name not in lookup:
            lookup[func.name] = SearchResult(function=func, score=0.0)
    return lookup


def _normalize_keyword_scores(
    keyword_results: list[SearchResult],
) -> dict[str, float]:
    """Normalize keyword scores to [0, 1]."""
    if not keyword_results:
        return {}
    raw = [r.score for r in keyword_results]
    lo, hi = min(raw), max(raw)
    span = hi - lo
    out: dict[str, float] = {}
    for r in keyword_results:
        out[r.function.name] = 1.0 if span == 0 else (r.score - lo) / span
    return out


def _normalize_vector_scores(
    vector_results: list[tuple[str, float]],
) -> dict[str, float]:
    """Normalize vector scores to [0, 1]."""
    if not vector_results:
        return {}
    raw = [max(s, 0.0) for _, s in vector_results]
    lo, hi = min(raw), max(raw)
    span = hi - lo
    out: dict[str, float] = {}
    for vid, score in vector_results:
        out[vid] = 1.0 if span == 0 else (max(score, 0.0) - lo) / span
    return out


def _classify_source(
    name: str,
    kw: dict[str, float],
    vec: dict[str, float],
) -> str:
    """Classify a result as keyword-only, vector-only, or hybrid."""
    in_kw = name in kw and kw[name] > 0
    in_vec = name in vec and vec[name] > 0
    if in_kw and in_vec:
        return "hybrid"
    if in_vec:
        return "vector"
    return "keyword"


if __name__ == "__main__":
    _self_path = Path(__file__) if "__file__" in globals() else Path("semantic_search.py")
    search = SemanticCodeSearch()
    search.index_file(_self_path)
    results = search.search("fuzz testing policy")
    for r in results:
        print(f"{r.function.name}: {r.score:.2f}")
