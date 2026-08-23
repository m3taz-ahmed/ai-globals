"""Cross-page (multipage) SEO issue checks.

Ported from open-seo (every-app/open-seo)
``src/server/lib/audit/issues/multipage.ts``.
Pure set-queries over crawl data — no fetching, no DOM. Runs over a
collection of :class:`~aizee_mcp.tools.seo_page_reporters.PageData`
records after the crawl completes.

Detects:
- Duplicate titles (same title across multiple URLs)
- Duplicate meta descriptions
- Duplicate content (same content hash)
- Redirect chains (A → B → C, 2+ hops)
- Redirect loops (A → B → A)
- Broken internal links (page links to a 4xx/5xx URL)
- Orphan pages (no internal links pointing to this page)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from runtime.seo_issue_registry import enrich_issue

from .seo_page_reporters import PageData


def find_duplicate_titles(pages: list[PageData]) -> list[dict[str, Any]]:
    """Find pages that share the same title tag."""
    by_title: dict[str, list[PageData]] = defaultdict(list)
    for page in pages:
        if page.fetch_class != "ok" or not page.is_html or not page.title:
            continue
        by_title[page.title].append(page)

    issues: list[dict[str, Any]] = []
    for title, group in by_title.items():
        if len(group) < 2:
            continue
        for page in group:
            issue: dict[str, Any] = {
                "issue_type": "duplicate-title",
                "page_url": page.url,
                "details": {
                    "title": title,
                    "duplicate_count": len(group),
                    "duplicate_urls": [p.url for p in group if p.url != page.url],
                },
            }
            issues.append(enrich_issue(issue))
    return issues


def find_duplicate_meta_descriptions(pages: list[PageData]) -> list[dict[str, Any]]:
    """Find pages that share the same meta description."""
    by_desc: dict[str, list[PageData]] = defaultdict(list)
    for page in pages:
        if page.fetch_class != "ok" or not page.is_html or not page.meta_description:
            continue
        by_desc[page.meta_description].append(page)

    issues: list[dict[str, Any]] = []
    for desc, group in by_desc.items():
        if len(group) < 2:
            continue
        for page in group:
            issue: dict[str, Any] = {
                "issue_type": "duplicate-meta-description",
                "page_url": page.url,
                "details": {
                    "description": desc[:100],
                    "duplicate_count": len(group),
                },
            }
            issues.append(enrich_issue(issue))
    return issues


def find_duplicate_content(pages: list[PageData]) -> list[dict[str, Any]]:
    """Find pages with byte-identical visible text (same content hash)."""
    by_hash: dict[str, list[PageData]] = defaultdict(list)
    for page in pages:
        if page.fetch_class != "ok" or not page.is_html or not page.content_hash:
            continue
        by_hash[page.content_hash].append(page)

    issues: list[dict[str, Any]] = []
    for content_hash, group in by_hash.items():
        if len(group) < 2:
            continue
        for page in group:
            issue: dict[str, Any] = {
                "issue_type": "duplicate-content",
                "page_url": page.url,
                "details": {
                    "content_hash": content_hash,
                    "duplicate_count": len(group),
                    "duplicate_urls": [p.url for p in group if p.url != page.url],
                },
            }
            issues.append(enrich_issue(issue))
    return issues


def find_redirect_chains_and_loops(pages: list[PageData]) -> list[dict[str, Any]]:
    """Find redirect chains (2+ hops) and redirect loops.

    Builds a redirect map from each page's ``redirect_url`` and
    traverses it to detect chains and loops.
    """
    redirect_map: dict[str, str | None] = {}
    for page in pages:
        if page.status_code >= 300 and page.status_code < 400:
            redirect_map[page.url] = page.redirect_url
        else:
            redirect_map[page.url] = None

    issues: list[dict[str, Any]] = []

    for page in pages:
        if page.status_code < 300 or page.status_code >= 400:
            continue
        if not page.redirect_url:
            continue

        # Traverse the chain
        visited: list[str] = [page.url]
        current: str | None = page.redirect_url
        is_loop = False
        chain_length = 1

        while current is not None and current in redirect_map:
            if current in visited:
                is_loop = True
                break
            visited.append(current)
            chain_length += 1
            current = redirect_map.get(current)

        if is_loop:
            issue: dict[str, Any] = {
                "issue_type": "redirect-loop",
                "page_url": page.url,
                "details": {"chain": visited},
            }
            issues.append(enrich_issue(issue))
        elif chain_length >= 2:
            issue = {
                "issue_type": "redirect-chain",
                "page_url": page.url,
                "details": {
                    "chain_length": chain_length,
                    "chain": visited,
                },
            }
            issues.append(enrich_issue(issue))

    return issues


def find_orphan_pages(
    pages: list[PageData],
    internal_links: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Find pages with no internal links pointing to them.

    *internal_links* maps ``source_url → [target_url, ...]``. If not
    provided, orphan detection is skipped (returns empty list) since
    we can't determine inlink count without link data.
    """
    if internal_links is None:
        return []

    # Build reverse link index: target_url → set of source_urls
    inlinks: dict[str, set[str]] = defaultdict(set)
    for source, targets in internal_links.items():
        for target in targets:
            inlinks[target].add(source)

    issues: list[dict[str, Any]] = []
    for page in pages:
        if page.fetch_class != "ok" or not page.is_html:
            continue
        if page.status_code >= 300:
            continue
        if len(inlinks.get(page.url, set())) == 0:
            issue: dict[str, Any] = {
                "issue_type": "orphan-page",
                "page_url": page.url,
                "details": {"inlink_count": 0},
            }
            issues.append(enrich_issue(issue))
    return issues


def find_broken_internal_links(
    pages: list[PageData],
    internal_links: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Find internal links pointing to pages that return 4xx/5xx.

    *internal_links* maps ``source_url → [target_url, ...]``. If not
    provided, broken link detection is skipped.
    """
    if internal_links is None:
        return []

    # Build status index: url → status_code
    status_by_url: dict[str, int] = {}
    for page in pages:
        status_by_url[page.url] = page.status_code

    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()  # (source, target) dedupe

    for source, targets in internal_links.items():
        for target in targets:
            if (source, target) in seen:
                continue
            target_status = status_by_url.get(target)
            if target_status is not None and target_status >= 400:
                seen.add((source, target))
                issue: dict[str, Any] = {
                    "issue_type": "broken-internal-link",
                    "page_url": source,
                    "details": {
                        "target_url": target,
                        "target_status": target_status,
                    },
                }
                issues.append(enrich_issue(issue))
    return issues


def run_multipage_checks(
    pages: list[PageData],
    internal_links: dict[str, list[str]] | None = None,
) -> list[dict[str, Any]]:
    """Run all cross-page checks and return a combined issue list."""
    issues: list[dict[str, Any]] = []
    issues.extend(find_duplicate_titles(pages))
    issues.extend(find_duplicate_meta_descriptions(pages))
    issues.extend(find_duplicate_content(pages))
    issues.extend(find_redirect_chains_and_loops(pages))
    issues.extend(find_orphan_pages(pages, internal_links))
    issues.extend(find_broken_internal_links(pages, internal_links))
    return issues
