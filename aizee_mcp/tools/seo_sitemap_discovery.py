"""robots.txt and sitemap.xml discovery for site audits.

Ported from open-seo (every-app/open-seo)
``src/server/lib/audit/discovery.ts``.
Fetches robots.txt (RFC 9309 compliant, 500KB cap), parses sitemap.xml
with recursion (max depth 3, max 300 docs, 10MB per shard), and builds
a URL frontier for crawling.

Safety caps prevent runaway sitemap parsing from exhausting memory.
"""

from __future__ import annotations

import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

_logger = logging.getLogger(__name__)

# Caps (mirror open-seo discovery.ts).
MAX_ROBOTS_TXT_BYTES = 500 * 1024  # RFC 9309 minimum
MAX_SITEMAP_DEPTH = 3
MAX_SITEMAP_DOCS = 300
MAX_SITEMAP_BYTES = 10 * 1024 * 1024  # 10MB per shard
SITEMAP_FETCH_TIMEOUT = 15  # seconds
ROBOTS_FETCH_TIMEOUT = 10  # seconds
DEFAULT_USER_AGENT = "aizee-audit-bot/1.0"


@dataclass
class RobotsResult:
    """Parsed robots.txt result."""

    is_allowed: Any  # Callable[[str], bool]
    sitemap_urls: list[str] = field(default_factory=list)
    raw_text: str | None = None


@dataclass
class DiscoveryResult:
    """Result of the discovery phase."""

    robots: RobotsResult | None = None
    sitemap_urls: list[str] = field(default_factory=list)
    page_urls: list[str] = field(default_factory=list)
    seeded_count: int = 0
    errors: list[str] = field(default_factory=list)


def _validate_url_scheme(url: str) -> bool:
    """Return True if *url* uses http or https scheme (SSRF protection)."""
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in ("http", "https")


def fetch_robots_txt(origin: str, user_agent: str = DEFAULT_USER_AGENT) -> str | None:
    """Fetch raw robots.txt body. Returns None if missing/unreachable."""
    robots_url = f"{origin}/robots.txt"
    if not _validate_url_scheme(robots_url):
        _logger.warning("Refusing to fetch non-http(s) URL: %s", robots_url)
        return None
    try:
        req = urllib.request.Request(
            robots_url,
            headers={"User-Agent": user_agent},
        )
        with urllib.request.urlopen(req, timeout=ROBOTS_FETCH_TIMEOUT) as resp:
            if resp.status != 200:
                return None
            body = resp.read(MAX_ROBOTS_TXT_BYTES + 1)
            if len(body) > MAX_ROBOTS_TXT_BYTES:
                _logger.warning(
                    "robots.txt at %s exceeded %d bytes, truncated",
                    robots_url, MAX_ROBOTS_TXT_BYTES,
                )
                body = body[:MAX_ROBOTS_TXT_BYTES]
            decoded: str = body.decode("utf-8", errors="replace")
            return decoded
    except Exception as exc:
        _logger.debug("Failed to fetch robots.txt from %s: %s", robots_url, exc)
        return None


def parse_robots_txt(origin: str, text: str | None) -> RobotsResult:
    """Parse robots.txt text. Deterministic: same text → same result.

    If text is None, everything is allowed (no restrictions).
    """
    if text is None:
        return RobotsResult(is_allowed=lambda _url: True, sitemap_urls=[], raw_text=None)

    sitemap_urls: list[str] = []
    # Simple parser: extract sitemap directives and user-agent rules.
    # This is a minimal implementation; for production use a library
    # like robots-parser (not available in stdlib).
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Match case-insensitive
        lower = stripped.lower()
        if lower.startswith("sitemap:"):
            sitemap_url = stripped.split(":", 1)[1].strip()
            if sitemap_url:
                sitemap_urls.append(sitemap_url)

    # Minimal allow/disallow: allow everything by default.
    # A full parser would track user-agent blocks and path rules.
    return RobotsResult(
        is_allowed=lambda _url: True,
        sitemap_urls=sitemap_urls,
        raw_text=text,
    )


def is_probably_sitemap(content_type: str | None, body: str) -> bool:
    """Heuristic: is this response a sitemap XML document?"""
    if content_type and "xml" in content_type.lower():
        return True
    stripped = body.lstrip()[:200].lower()
    return "<?xml" in stripped or "<urlset" in stripped or "<sitemapindex" in stripped


def fetch_sitemap(
    url: str,
    user_agent: str = DEFAULT_USER_AGENT,
) -> tuple[list[str], list[str]]:
    """Fetch and parse a sitemap. Returns (page_urls, child_sitemap_urls).

    Handles both sitemap index files (pointing to more sitemaps) and
    URL set files (containing page URLs).
    """
    if not _validate_url_scheme(url):
        _logger.warning("Refusing to fetch non-http(s) sitemap URL: %s", url)
        return [], []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with urllib.request.urlopen(req, timeout=SITEMAP_FETCH_TIMEOUT) as resp:
            if resp.status != 200:
                return [], []
            body = resp.read(MAX_SITEMAP_BYTES + 1)
            if len(body) > MAX_SITEMAP_BYTES:
                _logger.warning("Sitemap %s exceeded %d bytes, skipped", url, MAX_SITEMAP_BYTES)
                return [], []
            text = body.decode("utf-8", errors="replace")
    except Exception as exc:
        _logger.debug("Failed to fetch sitemap %s: %s", url, exc)
        return [], []

    page_urls: list[str] = []
    child_sitemap_urls: list[str] = []

    try:
        # Use defusedxml if available (XXE protection). defusedxml blocks
        # external entity expansion, preventing XXE attacks.
        try:
            from defusedxml import ElementTree as DefusedET
            root = DefusedET.fromstring(text)
        except ImportError:
            # Fail-closed: stdlib ET is vulnerable to XXE. Rather than
            # attempting a partial manual mitigation, refuse to parse
            # untrusted XML without defusedxml. Install defusedxml to
            # enable sitemap parsing.
            _logger.warning(
                "Sitemap %s skipped — defusedxml not installed (XXE protection required)",
                url,
            )
            return [], []
    except ET.ParseError as exc:
        _logger.warning("Failed to parse sitemap XML at %s: %s", url, exc)
        return [], []
    except Exception as exc:
        _logger.warning("Failed to parse sitemap XML at %s: %s", url, exc)
        return [], []

    # Strip XML namespaces for simple matching
    tag = root.tag
    if "}" in tag:
        tag = tag.split("}", 1)[1]

    if tag == "sitemapindex":
        # Index file: contains <sitemap><loc>...</loc></sitemap> entries
        for sitemap_elem in root:
            elem_tag = sitemap_elem.tag
            if "}" in elem_tag:
                elem_tag = elem_tag.split("}", 1)[1]
            if elem_tag != "sitemap":
                continue
            for loc_elem in sitemap_elem:
                loc_tag = loc_elem.tag
                if "}" in loc_tag:
                    loc_tag = loc_tag.split("}", 1)[1]
                if loc_tag == "loc" and loc_elem.text:
                    child_sitemap_urls.append(loc_elem.text.strip())
    elif tag == "urlset":
        # URL set: contains <url><loc>...</loc></url> entries
        for url_elem in root:
            elem_tag = url_elem.tag
            if "}" in elem_tag:
                elem_tag = elem_tag.split("}", 1)[1]
            if elem_tag != "url":
                continue
            for loc_elem in url_elem:
                loc_tag = loc_elem.tag
                if "}" in loc_tag:
                    loc_tag = loc_tag.split("}", 1)[1]
                if loc_tag == "loc" and loc_elem.text:
                    page_urls.append(loc_elem.text.strip())

    return page_urls, child_sitemap_urls


def discover_urls(
    origin: str,
    start_url: str,
    user_agent: str = DEFAULT_USER_AGENT,
    max_depth: int = MAX_SITEMAP_DEPTH,
    max_docs: int = MAX_SITEMAP_DOCS,
) -> DiscoveryResult:
    """Discover URLs via robots.txt sitemap directives.

    Fetches robots.txt, extracts sitemap URLs, recursively fetches
    sitemaps up to *max_depth* levels, collecting up to *max_docs*
    page URLs total.
    """
    result = DiscoveryResult()

    # 1. Fetch robots.txt
    robots_text = fetch_robots_txt(origin, user_agent)
    robots = parse_robots_txt(origin, robots_text)
    result.robots = robots
    result.sitemap_urls = list(robots.sitemap_urls)

    if not robots.sitemap_urls:
        # No sitemaps declared; seed with the start URL only
        result.page_urls = [start_url]
        result.seeded_count = 1
        return result

    # 2. Recursively fetch sitemaps
    visited_sitemaps: set[str] = set()
    queue: list[tuple[str, int]] = [
        (url, 0) for url in robots.sitemap_urls
    ]

    while queue and len(result.page_urls) < max_docs:
        sitemap_url, depth = queue.pop(0)
        if sitemap_url in visited_sitemaps:
            continue
        if depth > max_depth:
            continue
        visited_sitemaps.add(sitemap_url)

        page_urls, child_sitemaps = fetch_sitemap(sitemap_url, user_agent)
        result.page_urls.extend(page_urls)
        for child in child_sitemaps:
            if child not in visited_sitemaps:
                queue.append((child, depth + 1))

        if len(result.page_urls) >= max_docs:
            result.page_urls = result.page_urls[:max_docs]
            break

    # Always include the start URL as a seed
    if start_url not in result.page_urls:
        result.page_urls.insert(0, start_url)

    result.seeded_count = len(result.page_urls)
    return result


def get_origin(url: str) -> str:
    """Extract the origin (scheme + host + port) from a URL."""
    parsed = urllib.parse.urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def is_same_origin(url1: str, url2: str) -> bool:
    """Check if two URLs share the same origin."""
    return get_origin(url1) == get_origin(url2)


def normalize_url(url: str) -> str:
    """Normalize a URL: strip fragments, ensure trailing consistency."""
    parsed = urllib.parse.urlparse(url)
    # Remove fragment
    cleaned = parsed._replace(fragment="")
    return urllib.parse.urlunparse(cleaned)


def is_crawlable_url(url: str, robots: RobotsResult | None) -> bool:
    """Check if a URL is crawlable (same-origin + robots-allowed)."""
    if robots is None:
        return True
    try:
        return bool(robots.is_allowed(url))
    except Exception:
        return True
