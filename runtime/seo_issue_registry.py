"""Typed SEO audit issue registry.

Ported from open-seo (every-app/open-seo) ``src/shared/audit-issues.ts``.
Provides a single source of truth for SEO issue types, their severity,
human-readable explanation, and how-to-fix guidance. Used by the SEO
MCP tools (``seo_audit_page``, ``seo_audit_site``) to produce
structured, machine-readable issue reports instead of free-text prose.

Each issue type has:
- ``id``: stable machine-readable key (e.g. ``"missing-title"``)
- ``severity``: ``CRITICAL`` / ``WARNING`` / ``INFO``
- ``title``: short human-readable label
- ``explanation``: why it matters for SEO
- ``how_to_fix``: actionable remediation guidance

The registry is a frozen dict so it can be shared between the MCP
tools, the dashboard, and CSV/JSON export without drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class IssueSeverity(str, Enum):
    """Severity levels for SEO audit issues."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


# Ordering for display/sorting: critical first, then warning, then info.
SEVERITY_ORDER: dict[IssueSeverity, int] = {
    IssueSeverity.CRITICAL: 0,
    IssueSeverity.WARNING: 1,
    IssueSeverity.INFO: 2,
}


@dataclass(frozen=True)
class IssueDescriptor:
    """Descriptor for one SEO audit issue type."""

    id: str
    severity: IssueSeverity
    title: str
    explanation: str
    how_to_fix: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a structured dict for JSON/CSV export."""
        return {
            "id": self.id,
            "severity": self.severity.value,
            "title": self.title,
            "explanation": self.explanation,
            "how_to_fix": self.how_to_fix,
        }


# ---------------------------------------------------------------------------
# Issue registry — the single source of truth.
# Mirrors open-seo's AUDIT_ISSUE_TYPES with aiZee-specific additions.
# ---------------------------------------------------------------------------

_ISSUES: dict[str, IssueDescriptor] = {}


def _register(
    issue_id: str,
    severity: IssueSeverity,
    title: str,
    explanation: str,
    how_to_fix: str,
) -> None:
    """Register an issue descriptor. Called at module load."""
    _ISSUES[issue_id] = IssueDescriptor(
        id=issue_id,
        severity=severity,
        title=title,
        explanation=explanation,
        how_to_fix=how_to_fix,
    )


# -- Critical issues --------------------------------------------------------

_register(
    "blocked-page", IssueSeverity.CRITICAL,
    "Crawler was blocked",
    "The site returned a bot challenge or access denial (e.g. Cloudflare challenge, 403, 429) instead of the page. The page could not be audited, and search engines may face similar friction.",
    'Allowlist the audit user agent in your WAF/bot-protection settings, then re-run the audit.',
)
_register(
    "server-error", IssueSeverity.CRITICAL,
    "Server error (5xx)",
    "The page returned a 5xx server error. Search engines that repeatedly see server errors will crawl the site less and may drop the page from the index.",
    "Check server logs for this URL and fix the underlying error. If the page is gone, return 404/410 or redirect to a relevant page.",
)
_register(
    "broken-internal-link", IssueSeverity.CRITICAL,
    "Broken internal link",
    "This page links to an internal URL that returns an error status (4xx/5xx). Broken links waste crawl budget, leak link equity, and frustrate users.",
    "Update the link to point at the correct live URL, or remove it. Prefer direct links over relying on redirects.",
)
_register(
    "missing-title", IssueSeverity.CRITICAL,
    "Missing title tag",
    "The page has no <title>. The title is the strongest on-page relevance signal and the headline in search results; without it search engines generate one, usually badly.",
    "Add a unique, descriptive <title> of roughly 50-60 characters that includes the page's primary topic.",
)
_register(
    "missing-canonical", IssueSeverity.CRITICAL,
    "Missing canonical",
    "The page has no rel=canonical tag. Without it, search engines may index duplicate or variant URLs separately, splitting ranking signals.",
    "Add a <link rel=\"canonical\" href=\"...\"> tag pointing to the preferred URL for this content.",
)

# -- Warning issues ---------------------------------------------------------

_register(
    "broken-page", IssueSeverity.WARNING,
    "Page returns an error (4xx)",
    "This crawled URL returned a client error (e.g. 404). If referenced from sitemap or internal links, crawlers keep wasting requests on it.",
    "If the page should exist, restore it. If intentionally gone, remove from sitemap and internal links, and consider a 301 redirect to the closest live page.",
)
_register(
    "duplicate-title", IssueSeverity.WARNING,
    "Duplicate title",
    "Multiple pages share the same title tag. Search engines use titles to differentiate pages; duplicates make pages compete and depress CTR.",
    "Write a unique title for each page describing its specific content. For templated pages, include the distinguishing attribute in the template.",
)
_register(
    "duplicate-meta-description", IssueSeverity.WARNING,
    "Duplicate meta description",
    "Multiple pages share the same meta description, so search results show identical snippets and users cannot tell the pages apart.",
    "Write a unique meta description per page, or remove the duplicated one entirely — search engines will generate a snippet from content.",
)
_register(
    "duplicate-content", IssueSeverity.WARNING,
    "Duplicate page content",
    "Two or more URLs serve byte-identical visible text. Search engines pick one version to index and ignore the rest, splitting ranking signals.",
    "Consolidate duplicates: pick the canonical URL, add rel=canonical from the others, and 301-redirect duplicate URLs where possible.",
)
_register(
    "missing-meta-description", IssueSeverity.WARNING,
    "Missing meta description",
    "The page has no meta description. Search engines will assemble a snippet from page text, which is often less compelling and hurts CTR.",
    "Add a meta description of roughly 70-160 characters that summarizes the page and gives a reason to click.",
)
_register(
    "missing-h1", IssueSeverity.WARNING,
    "Missing H1 heading",
    "The page has no H1. The H1 tells users and search engines what the page is about; pages without one tend to have weaker topical clarity.",
    "Add a single H1 that states the page's main topic, consistent with the title tag.",
)
_register(
    "multiple-h1", IssueSeverity.WARNING,
    "Multiple H1 headings",
    "The page has more than one H1, which dilutes the main-topic signal and usually indicates a templating mistake.",
    "Keep one H1 for the page's main heading and demote the others to H2/H3.",
)
_register(
    "redirect-chain", IssueSeverity.WARNING,
    "Redirect chain",
    "Reaching the final page requires two or more consecutive redirects. Each hop adds latency, leaks link equity, and burns crawl budget.",
    "Point the first URL (and any internal links) directly at the final destination so there is at most one redirect.",
)
_register(
    "redirect-loop", IssueSeverity.WARNING,
    "Redirect loop",
    "This redirect eventually points back to itself, so the URL never resolves. Browsers and crawlers give up with an error.",
    "Find and break the loop. Check redirect maps and server config for circular references.",
)
_register(
    "title-too-long", IssueSeverity.WARNING,
    "Title too long",
    "The title exceeds 60 characters. Search engines truncate long titles in results, potentially cutting off important keywords.",
    "Shorten the title to 50-60 characters while keeping the primary keyword near the front.",
)
_register(
    "title-too-short", IssueSeverity.WARNING,
    "Title too short",
    "The title is under 10 characters, which is too brief to convey the page's topic to users or search engines.",
    "Expand the title to at least 10-15 characters with a descriptive phrase including the primary topic.",
)
_register(
    "meta-description-too-long", IssueSeverity.WARNING,
    "Meta description too long",
    "The meta description exceeds 160 characters. Search engines truncate long descriptions in results.",
    "Shorten the meta description to 70-160 characters while keeping the key selling point.",
)
_register(
    "meta-description-too-short", IssueSeverity.WARNING,
    "Meta description too short",
    "The meta description is under 70 characters, which is too brief to be compelling in search results.",
    "Expand the meta description to 70-160 characters with a clear summary and call to action.",
)
_register(
    "heading-order-skip", IssueSeverity.WARNING,
    "Heading order skip",
    "Heading levels are skipped (e.g. H1 → H3 without an H2), which breaks the document outline and confuses screen readers and search engines.",
    "Fix the heading hierarchy so levels increase sequentially (H1 → H2 → H3).",
)
_register(
    "noindex-page", IssueSeverity.WARNING,
    "Page blocked from indexing",
    "The page has a noindex directive (robots meta or X-Robots-Tag), so search engines will not index it.",
    "If this page should be indexed, remove the noindex directive. If intentionally excluded, this is expected.",
)
_register(
    "orphan-page", IssueSeverity.WARNING,
    "Orphan page",
    "This page has no internal links pointing to it from other crawled pages. Orphan pages are hard for crawlers and users to discover.",
    "Add internal links from relevant pages to this URL, or remove it if it should not exist.",
)
_register(
    "thin-content", IssueSeverity.WARNING,
    "Thin content",
    "The page has very little visible text (under 150 words). Thin content provides little value to users and search engines.",
    "Expand the page with substantive, original content that serves the user's intent. Aim for at least 300 words for informational pages.",
)
_register(
    "slow-response", IssueSeverity.WARNING,
    "Slow server response",
    "The page took over 1.5 seconds to respond. Slow responses hurt crawl budget and Core Web Vitals (LCP).",
    "Optimize server response time (TTFB). Target under 600ms. Check database queries, caching, and CDN configuration.",
)
_register(
    "images-missing-alt", IssueSeverity.WARNING,
    "Images missing alt text",
    "One or more images on the page lack alt text. Alt text is an accessibility signal and helps image search visibility.",
    "Add descriptive alt text to all informative images. Use empty alt (alt=\"\") for purely decorative images.",
)
_register(
    "images-missing-dims", IssueSeverity.INFO,
    "Images missing dimensions",
    "One or more images lack width/height attributes, causing layout shift (CLS).",
    "Add explicit width and height attributes (or aspect-ratio CSS) to all images.",
)
_register(
    "og-title-missing", IssueSeverity.INFO,
    "Missing og:title",
    "The page has no Open Graph title, so social shares fall back to the document title.",
    "Add an og:title meta tag tuned for social sharing.",
)
_register(
    "og-desc-missing", IssueSeverity.INFO,
    "Missing og:description",
    "The page has no Open Graph description, so social shares lack a summary.",
    "Add an og:description meta tag tuned for social sharing.",
)

# -- Info issues ------------------------------------------------------------

_register(
    "deep-page", IssueSeverity.INFO,
    "Deep page (high click depth)",
    "This page is more than 5 clicks from the homepage. Deep pages may be crawled less frequently and receive less link equity.",
    "Reduce click depth by adding internal links from higher-level pages or restructuring navigation.",
)
_register(
    "canonical-mismatch", IssueSeverity.INFO,
    "Canonical mismatch",
    "The rel=canonical URL does not match the page's URL, which may be intentional (for duplicate consolidation) or a mistake.",
    "Verify the canonical URL is correct. If pointing to a different URL intentionally, ensure the target exists and is indexable.",
)
_register(
    "missing-hreflang", IssueSeverity.INFO,
    "Missing hreflang",
    "The page has no hreflang tags. For multi-language sites, hreflang helps search engines serve the correct language version.",
    "Add hreflang tags for each language version of the page, including a self-referencing entry.",
)
_register(
    "missing-structured-data", IssueSeverity.INFO,
    "Missing structured data",
    "The page has no JSON-LD structured data. Schema markup helps search engines understand content and enables rich results.",
    "Add relevant JSON-LD schema (e.g. Article, Product, FAQPage) matching the page's content type.",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_issue_descriptor(issue_id: str) -> IssueDescriptor | None:
    """Return the descriptor for *issue_id*, or ``None`` if unknown."""
    return _ISSUES.get(issue_id)


def get_all_issues() -> dict[str, IssueDescriptor]:
    """Return a copy of the full issue registry."""
    return dict(_ISSUES)


def get_issues_by_severity(severity: IssueSeverity) -> list[IssueDescriptor]:
    """Return all issue descriptors matching *severity*."""
    return [d for d in _ISSUES.values() if d.severity == severity]


def sort_issues_by_severity(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort a list of issue dicts by severity (critical first).

    Each dict is expected to have an ``issue_type`` or ``id`` key whose
    value is a registered issue ID.
    """
    def _key(issue: dict[str, Any]) -> int:
        issue_id = issue.get("issue_type") or issue.get("id", "")
        descriptor = _ISSUES.get(str(issue_id))
        if descriptor is None:
            return 99  # Unknown issues sort last
        return SEVERITY_ORDER.get(descriptor.severity, 99)

    return sorted(issues, key=_key)


def issue_count_by_severity(issues: list[dict[str, Any]]) -> dict[str, int]:
    """Count issues by severity. Returns ``{"critical": N, "warning": N, "info": N}``."""
    counts: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    for issue in issues:
        issue_id = str(issue.get("issue_type") or issue.get("id", ""))
        descriptor = _ISSUES.get(issue_id)
        if descriptor is not None:
            counts[descriptor.severity.value] += 1
    return counts


def enrich_issue(issue: dict[str, Any]) -> dict[str, Any]:
    """Enrich a raw issue dict with its descriptor metadata.

    Adds ``severity``, ``title``, ``explanation``, and ``how_to_fix``
    from the registry if the issue ID is known. The original dict is
    not modified; a new dict is returned.
    """
    issue_id = str(issue.get("issue_type") or issue.get("id", ""))
    descriptor = _ISSUES.get(issue_id)
    if descriptor is None:
        return dict(issue)
    enriched = dict(issue)
    enriched["severity"] = descriptor.severity.value
    enriched["title"] = descriptor.title
    enriched["explanation"] = descriptor.explanation
    enriched["how_to_fix"] = descriptor.how_to_fix
    return enriched
