"""Gap tests for aizee_mcp/tools/seo_page_reporters.py — every branch."""
from __future__ import annotations

from aizee_mcp.tools.seo_page_reporters import (
    PageData,
    _has_heading_level_skip,
    run_page_reporters,
)


def _page(**kw) -> PageData:
    return PageData(url="https://ex.com/p", **kw)


def _types(issues):
    return {i["issue_type"] for i in issues}


def test_blocked_page():
    out = run_page_reporters(_page(fetch_class="blocked", status_code=403))
    assert _types(out) == {"blocked-page"}


def test_error_page():
    out = run_page_reporters(_page(fetch_class="error", status_code=0))
    assert _types(out) == {"server-error"}


def test_5xx():
    out = run_page_reporters(_page(status_code=503))
    assert _types(out) == {"server-error"}


def test_4xx():
    out = run_page_reporters(_page(status_code=404))
    assert _types(out) == {"broken-page"}


def test_3xx():
    out = run_page_reporters(_page(status_code=301, redirect_url="https://ex.com/new"))
    assert _types(out) == {"redirect-chain"}


def test_slow_response_non_html():
    out = run_page_reporters(_page(response_time_ms=2000, is_html=False))
    assert _types(out) == {"slow-response"}


def test_title_lengths():
    long = run_page_reporters(_page(title="t" * 70, h1_count=1, is_indexable=True,
                                    canonical_url="https://ex.com/p", word_count=200,
                                    og_title="o", og_description="d",
                                    has_structured_data=True, has_hreflang=True))
    assert "title-too-long" in _types(long)
    short = run_page_reporters(_page(title="tiny", h1_count=1, canonical_url="https://ex.com/p",
                                     word_count=200, og_title="o", og_description="d",
                                     has_structured_data=True, has_hreflang=True))
    assert "title-too-short" in _types(short)
    missing = run_page_reporters(_page(h1_count=1, canonical_url="https://ex.com/p",
                                       word_count=200, og_title="o", og_description="d",
                                       has_structured_data=True, has_hreflang=True))
    assert "missing-title" in _types(missing)


def test_meta_description_lengths():
    base = {"title": "good title here", "h1_count": 1, "canonical_url": "https://ex.com/p",
                "word_count": 200, "og_title": "o", "og_description": "d",
                "has_structured_data": True, "has_hreflang": True}
    long = run_page_reporters(_page(meta_description="m" * 200, **base))
    assert "meta-description-too-long" in _types(long)
    short = run_page_reporters(_page(meta_description="short", **base))
    assert "meta-description-too-short" in _types(short)
    missing = run_page_reporters(_page(**base))
    assert "missing-meta-description" in _types(missing)


def test_headings():
    assert _has_heading_level_skip([1, 3])
    assert not _has_heading_level_skip([1, 2, 3])
    assert not _has_heading_level_skip([])
    multi = run_page_reporters(_page(title="good title here", h1_count=3,
                                     canonical_url="https://ex.com/p", word_count=200,
                                     meta_description="m" * 100, og_title="o",
                                     og_description="d", has_structured_data=True,
                                     has_hreflang=True))
    assert "multiple-h1" in _types(multi)
    skip = run_page_reporters(_page(title="good title here", h1_count=1,
                                    heading_order=[1, 4],
                                    canonical_url="https://ex.com/p", word_count=200,
                                    meta_description="m" * 100, og_title="o",
                                    og_description="d", has_structured_data=True,
                                    has_hreflang=True))
    assert "heading-order-skip" in _types(skip)


def test_noindex_and_canonical():
    out = run_page_reporters(_page(
        title="good title here", h1_count=1, meta_description="m" * 100,
        word_count=200, is_indexable=False, robots_meta="noindex",
        x_robots_tag="none", canonical_url="https://ex.com/other",
        og_title="o", og_description="d", has_structured_data=True, has_hreflang=True))
    types = _types(out)
    assert "noindex-page" in types
    assert "canonical-mismatch" in types
    missing = run_page_reporters(_page(title="good title here", h1_count=1,
                                       meta_description="m" * 100, word_count=200,
                                       og_title="o", og_description="d",
                                       has_structured_data=True, has_hreflang=True))
    assert "missing-canonical" in _types(missing)


def test_thin_images_og_structured_hreflang_deep():
    out = run_page_reporters(_page(
        title="good title here", h1_count=1, meta_description="m" * 100,
        canonical_url="https://ex.com/p", word_count=10,
        images_missing_alt=2, images_missing_dims=1, page_depth=7))
    types = _types(out)
    assert {"thin-content", "images-missing-alt", "images-missing-dims",
            "og-title-missing", "og-desc-missing", "missing-structured-data",
            "missing-hreflang", "deep-page"} <= types


def test_clean_page_no_issues():
    out = run_page_reporters(_page(
        title="a perfectly sized title", h1_count=1, heading_order=[1, 2],
        meta_description="a" * 100, canonical_url="https://ex.com/p",
        word_count=300, og_title="o", og_description="d",
        has_structured_data=True, has_hreflang=True, page_depth=1))
    assert out == []
