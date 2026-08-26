"""Per-page SEO issue reporters.

Ported from open-seo (every-app/open-seo)
``src/server/lib/audit/issues/page-reporters.ts``.
Each reporter is a pure function over a single crawled page's parsed
data — no DOM, no fetching. The engine works over any crawl source
that can produce a :class:`PageData` record.

Cross-page checks (duplicates, broken links, orphans, redirect chains)
were previously in a separate module and have been consolidated into the
SEO audit engine; they run over a collection of pages after the crawl.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from runtime.seo_issue_registry import enrich_issue

# Thresholds (mirrors open-seo page-reporters.ts constants).
TITLE_MAX_CHARS = 60
TITLE_MIN_CHARS = 10
META_DESCRIPTION_MAX_CHARS = 160
META_DESCRIPTION_MIN_CHARS = 70
THIN_CONTENT_WORDS = 150
SLOW_RESPONSE_MS = 1500
DEEP_PAGE_DEPTH = 5


@dataclass
class PageData:
    """Parsed SEO data for a single crawled page.

    Produced by the HTML parser in ``seo_tools.py``. This is the input
    to all per-page reporters.
    """

    url: str
    status_code: int = 200
    response_time_ms: float = 0.0
    fetch_class: str = "ok"  # "ok", "blocked", "error", "redirect"
    is_html: bool = True
    title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    h1_count: int = 0
    heading_order: list[int] = field(default_factory=list)
    is_indexable: bool = True
    robots_meta: str | None = None
    x_robots_tag: str | None = None
    word_count: int = 0
    content_hash: str | None = None
    images_missing_alt: int = 0
    images_missing_dims: int = 0
    og_title: str | None = None
    og_description: str | None = None
    has_structured_data: bool = False
    has_hreflang: bool = False
    redirect_url: str | None = None
    page_depth: int = 0


def _has_heading_level_skip(heading_order: list[int]) -> bool:
    """Return True if heading levels skip (e.g. H1 → H3 without H2)."""
    return any(heading_order[i] > heading_order[i - 1] + 1 for i in range(1, len(heading_order)))


def run_page_reporters(page: PageData) -> list[dict[str, Any]]:
    """Run all per-page reporters and return a list of enriched issues.

    Each issue dict includes the issue type ID plus enriched metadata
    (severity, title, explanation, how_to_fix) from the
    :mod:`runtime.seo_issue_registry`.
    """
    issues: list[dict[str, Any]] = []

    def report(issue_type: str, details: dict[str, Any] | None = None) -> None:
        issue: dict[str, Any] = {"issue_type": issue_type, "page_url": page.url}
        if details:
            issue["details"] = details
        issues.append(enrich_issue(issue))

    # Blocked / error pages
    if page.fetch_class == "blocked":
        report("blocked-page", {"statusCode": page.status_code})
        return issues
    if page.fetch_class == "error":
        return issues

    # Status code checks
    if page.status_code >= 500:
        report("server-error", {"statusCode": page.status_code})
        return issues
    if page.status_code >= 400:
        report("broken-page", {"statusCode": page.status_code})
        return issues
    if page.status_code >= 300:
        return issues  # Redirects are normal; chains/loops flagged in multipage

    # Slow response
    if page.response_time_ms > SLOW_RESPONSE_MS:
        report("slow-response", {"responseTimeMs": page.response_time_ms})

    # Content checks only for HTML
    if not page.is_html:
        return issues

    # Title
    if not page.title:
        report("missing-title")
    elif len(page.title) > TITLE_MAX_CHARS:
        report("title-too-long", {"length": len(page.title)})
    elif len(page.title) < TITLE_MIN_CHARS:
        report("title-too-short", {"length": len(page.title)})

    # Meta description
    if not page.meta_description:
        report("missing-meta-description")
    elif len(page.meta_description) > META_DESCRIPTION_MAX_CHARS:
        report("meta-description-too-long", {"length": len(page.meta_description)})
    elif len(page.meta_description) < META_DESCRIPTION_MIN_CHARS:
        report("meta-description-too-short", {"length": len(page.meta_description)})

    # Headings
    if page.h1_count == 0:
        report("missing-h1")
    elif page.h1_count > 1:
        report("multiple-h1", {"h1Count": page.h1_count})
    if _has_heading_level_skip(page.heading_order):
        report("heading-order-skip")

    # Indexability
    if not page.is_indexable:
        report("noindex-page", {
            "robotsMeta": page.robots_meta,
            "xRobotsTag": page.x_robots_tag,
        })

    # Canonical
    if not page.canonical_url:
        report("missing-canonical")
    elif page.canonical_url != page.url:
        report("canonical-mismatch", {"canonicalUrl": page.canonical_url})

    # Thin content
    if page.word_count < THIN_CONTENT_WORDS:
        report("thin-content", {"wordCount": page.word_count})

    # Images
    if page.images_missing_alt > 0:
        report("images-missing-alt", {"count": page.images_missing_alt})

    # Structured data
    if not page.has_structured_data:
        report("missing-structured-data")

    # Hreflang
    if not page.has_hreflang:
        report("missing-hreflang")

    # Deep page
    if page.page_depth > DEEP_PAGE_DEPTH:
        report("deep-page", {"depth": page.page_depth})

    return issues
