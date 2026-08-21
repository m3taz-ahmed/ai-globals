#!/usr/bin/env python3
"""SEO MCP tools: page audit, site audit, CWV, schema validation, content analysis, GEO/AEO, GSC, opportunities.

All tools use free APIs (PageSpeed Insights, GSC) or stdlib HTTP (urllib).
No paid APIs (DataForSEO) and no heavy dependencies (Playwright).
"""

from __future__ import annotations

import hashlib
import html.parser
import ipaddress
import json
import re
import ssl
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from typing import Any

from aizee_mcp._compat import FastMCP  # pyright: ignore

from .common import _MAX_INPUT_LENGTH, truncate, validate_query

# --- Constants -------------------------------------------------------------

_USER_AGENT = "aizee-seo-bot/1.0 (+https://github.com/aizee)"
_TIMEOUT = 15  # seconds
_MAX_PAGES = 2000
_MAX_CONTENT_LENGTH = 2_000_000  # 2MB HTML limit (Googlebot's limit)

_CWV_THRESHOLDS: dict[str, dict[str, float]] = {
    "lcp": {"good": 2.5, "poor": 4.0},
    "inp": {"good": 200.0, "poor": 500.0},
    "cls": {"good": 0.1, "poor": 0.25},
    "ttfb": {"good": 800.0, "poor": 1800.0},
    "fcp": {"good": 1.8, "poor": 3.0},
}

_ACTIVE_SCHEMA_TYPES = {
    "Organization", "WebSite", "Article", "Product", "BreadcrumbList",
    "LocalBusiness", "Event", "Person", "JobPosting", "Course",
    "Review", "AggregateRating", "VideoObject", "ImageObject",
    "DiscussionForumPosting", "ProductGroup", "Offer",
}

_DEPRECATED_SCHEMA_TYPES = {
    "HowTo", "SpecialAnnouncement", "CourseInfo", "EstimatedSalary",
    "LearningVideo", "ClaimReview", "VehicleListing", "PracticeProblem",
    "FAQPage",  # retired May 2026 for rich results
}

_AI_CRAWLERS = {
    "GPTBot", "ChatGPT-User", "OpenAI-SearchBot", "ClaudeBot",
    "PerplexityBot", "Google-Extended", "Google-Agent", "CCBot", "GrokBot",
}

_SEVERITY_PENALTY: dict[str, int] = {"CRITICAL": -8, "WARNING": -3, "INFO": -1}

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_SCHEMES = {"javascript", "data", "file", "ftp", "mailto"}
_CWV_STRATEGIES = {"mobile", "desktop"}
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "ref"}

# Pre-compiled regexes for _strip_html (performance: avoid re-compilation on every call)
_CDATA_RE = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SCRIPT_RE = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[^>]*>.*?</style>", re.DOTALL | re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_CHARSET_RE = re.compile(r"charset=([\w\-]+)", re.IGNORECASE)

# --- URL validation --------------------------------------------------------


def _is_private_ip(host: str) -> bool:
    """Check if host is a private/loopback/link-local/reserved IP address."""
    if not host:
        return False
    # Strip brackets from IPv6 addresses if present
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    # Strip port for IPv4 (e.g. "127.0.0.1:8080" → "127.0.0.1")
    # For IPv6, urlparse.hostname() already strips brackets and port
    if host.count(":") == 1:  # IPv4:port
        host = host.split(":")[0]
    # Check for localhost by name
    if host.lower() in ("localhost",):
        return True
    try:
        ip = ipaddress.ip_address(host)
        # Block 0.0.0.0 (unspecified) + all private/reserved ranges
        if ip.is_unspecified:
            return True
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast
    except ValueError:
        # Not an IP address (it's a domain) — check DNS resolution for rebinding
        return _resolves_to_private_ip(host)


def _resolves_to_private_ip(host: str) -> bool:
    """Check if a hostname resolves to a private IP address (DNS rebinding protection)."""
    import socket
    try:
        addrinfo = socket.getaddrinfo(host, None)
        for _, _, _, _, sockaddr in addrinfo:
            ip_str: str = str(sockaddr[0])
            # Handle IPv4-mapped IPv6 addresses
            if ip_str.startswith("::ffff:"):
                ip_str = ip_str[7:]
            try:
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
                    return True
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        pass  # DNS resolution failed — let the fetch attempt proceed
    return False


class _SsrfSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Redirect handler that validates each redirect target against SSRF rules."""

    def redirect_request(  # type: ignore[no-untyped-def]
        self, req, fp, code, msg, hdrs, newurl, method=None,
    ):
        # Resolve relative redirect URLs against the original request URL
        absolute_url = urllib.parse.urljoin(req.full_url, newurl)
        # Validate redirect target — block redirects to private/internal IPs
        if _validate_url(absolute_url) is not None:
            return None  # Block redirect to unsafe target
        return super().redirect_request(req, fp, code, msg, hdrs, absolute_url)


def _validate_url(url: str) -> str | None:
    """Return error JSON if URL is invalid, None if valid. Blocks SSRF targets."""
    if not isinstance(url, str) or not url or len(url) > _MAX_INPUT_LENGTH:
        return json.dumps({"ok": False, "error": "Invalid URL"})
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in _BLOCKED_SCHEMES:
        return json.dumps({"ok": False, "error": f"URL scheme '{parsed.scheme}' is not allowed"})
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return json.dumps({"ok": False, "error": "URL must use http or https"})
    if not parsed.netloc:
        return json.dumps({"ok": False, "error": "URL must have a domain"})
    # SSRF protection: block private/loopback/link-local IP ranges
    if _is_private_ip(parsed.hostname or ""):
        return json.dumps({"ok": False, "error": "Private/internal IP addresses are not allowed"})
    return None


def _normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters and fragment."""
    parsed = urllib.parse.urlparse(url)
    if parsed.query:
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        filtered = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}
        new_query = urllib.parse.urlencode(filtered, doseq=True)
        parsed = parsed._replace(query=new_query)
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


# Cached SSRF-safe opener (built once, reused across fetches)
_SEO_OPENER: urllib.request.OpenerDirector | None = None


def _get_opener() -> urllib.request.OpenerDirector:
    """Return cached SSRF-safe opener (built once for performance)."""
    global _SEO_OPENER
    if _SEO_OPENER is None:
        ctx = ssl.create_default_context()
        _SEO_OPENER = urllib.request.build_opener(_SsrfSafeRedirectHandler, urllib.request.HTTPSHandler(context=ctx))
    return _SEO_OPENER


def _fetch(url: str) -> tuple[int | None, str, dict[str, str]]:
    """Fetch URL content. Returns (status_code, body, headers). On error returns (None, "", {})."""
    err = _validate_url(url)
    if err:
        return None, "", {}
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "text/html"})
    try:
        with _get_opener().open(req, timeout=_TIMEOUT) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return resp.status, "", dict(resp.headers)
            # Parse charset from Content-Type (default utf-8)
            charset = "utf-8"
            ct_match = _CHARSET_RE.search(content_type)
            if ct_match:
                charset = ct_match.group(1)
            body = resp.read(_MAX_CONTENT_LENGTH).decode(charset, errors="replace")
            return resp.status, body, dict(resp.headers)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, LookupError):
        # LookupError covers unknown charset encoding; HTTPError for blocked redirects
        return None, "", {}


# --- HTML parser -----------------------------------------------------------


class _SeoHtmlParser(html.parser.HTMLParser):
    """Minimal HTML parser extracting SEO-relevant elements."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str = ""
        self.meta: dict[str, str] = {}
        self.h1s: list[str] = []
        self.h2s: list[str] = []
        self.h3s: list[str] = []
        self.links: list[dict[str, str]] = []
        self.images: list[dict[str, str]] = []
        self.canonical: str = ""
        self.json_ld: list[str] = []
        self.og_tags: dict[str, str] = {}
        self._in_title = False
        self._in_script = False
        self._script_type = ""
        self._script_content: list[str] = []
        self._tag_stack: list[str] = []
        self._current_attrs: dict[str, str] = {}
        self._in_a = False
        self._current_link_href = ""
        self._current_link_text: list[str] = []

    @property
    def _current_tag(self) -> str:
        """Current tag is the top of the stack (handles nesting correctly)."""
        return self._tag_stack[-1] if self._tag_stack else ""

    def _handle_meta_tag(self, attr_dict: dict[str, str]) -> None:
        name = attr_dict.get("name", "").lower()
        prop = attr_dict.get("property", "").lower()
        content = attr_dict.get("content", "")
        if name and content:
            self.meta[name] = content
        if prop and content:
            self.og_tags[prop] = content

    def _handle_link_tag(self, attr_dict: dict[str, str]) -> None:
        rel = attr_dict.get("rel", "").lower()
        href = attr_dict.get("href", "")
        if rel == "canonical" and href:
            self.canonical = href

    def _handle_img_tag(self, attr_dict: dict[str, str]) -> None:
        self.images.append({
            "src": attr_dict.get("src", ""),
            "alt": attr_dict.get("alt", ""),
            "width": attr_dict.get("width", ""),
            "height": attr_dict.get("height", ""),
        })

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: (v or "") for k, v in attrs}
        self._tag_stack.append(tag)
        self._current_attrs = attr_dict
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self._handle_meta_tag(attr_dict)
        elif tag == "link":
            self._handle_link_tag(attr_dict)
        elif tag == "a":
            self._in_a = True
            self._current_link_href = attr_dict.get("href", "")
            self._current_link_text = []
        elif tag == "img":
            self._handle_img_tag(attr_dict)
        elif tag == "script":
            self._in_script = True
            self._script_type = attr_dict.get("type", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a" and self._in_a:
            self.links.append({
                "href": self._current_link_href,
                "text": "".join(self._current_link_text).strip(),
            })
            self._in_a = False
            self._current_link_href = ""
            self._current_link_text = []
        elif tag == "script" and self._in_script:
            content = "".join(self._script_content)
            if self._script_type == "application/ld+json" and content.strip():
                self.json_ld.append(content.strip())
            self._in_script = False
            self._script_type = ""
            self._script_content = []
        # Pop tag from stack (handles nested identical tags correctly)
        if self._tag_stack and tag in self._tag_stack:
            # Pop until we find the matching tag (handles malformed nesting)
            while self._tag_stack:
                popped = self._tag_stack.pop()
                if popped == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._in_script:
            self._script_content.append(data)
        elif self._in_a:
            self._current_link_text.append(data)
        elif self._current_tag in ("h1", "h2", "h3"):
            text = data.strip()
            if text:
                if self._current_tag == "h1":
                    self.h1s.append(text)
                elif self._current_tag == "h2":
                    self.h2s.append(text)
                else:
                    self.h3s.append(text)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Self-closing tag — process but don't push to stack
        attr_dict = {k: (v or "") for k, v in attrs}
        if tag == "meta":
            self._handle_meta_tag(attr_dict)
        elif tag == "link":
            self._handle_link_tag(attr_dict)
        elif tag == "img":
            self._handle_img_tag(attr_dict)
        # Don't push to stack — self-closing tags have no content


def _parse_html(body: str) -> _SeoHtmlParser:
    parser = _SeoHtmlParser()
    try:
        parser.feed(body)
    except Exception:  # Malformed HTML is common; return partial results
        pass
    finally:
        parser.close()
    return parser


# --- Text helpers ----------------------------------------------------------


def _strip_html(body: str) -> str:
    """Strip HTML tags, scripts, styles, CDATA, comments. Return visible text."""
    body = _CDATA_RE.sub("", body)
    body = _COMMENT_RE.sub("", body)
    body = _SCRIPT_RE.sub("", body)
    body = _STYLE_RE.sub("", body)
    body = _TAG_RE.sub(" ", body)
    body = _WHITESPACE_RE.sub(" ", body)
    return body.strip()


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _flesch_reading_ease(text: str) -> float:
    """Approximate Flesch Reading Ease score (0-100)."""
    if not text:
        return 0.0
    words = text.split()
    n_words = len(words)
    if n_words == 0:
        return 0.0
    sentences = re.split(r"[.!?]+", text)
    n_sentences = max(1, len([s for s in sentences if s.strip()]))
    syllables = sum(_count_syllables(w) for w in words)
    if n_words == 0 or n_sentences == 0:
        return 0.0
    return max(0.0, min(100.0, 206.835 - 1.015 * (n_words / n_sentences) - 84.6 * (syllables / n_words)))


def _count_syllables(word: str) -> int:
    word = word.lower().strip()
    if not word or not word.isalpha():
        return 0  # Numbers and symbols have 0 syllables
    count = len(re.findall(r"[aeiouy]+", word))
    if word.endswith("e") and count > 1:
        count -= 1
    # Words with no vowel matches (e.g. "fly", "my", "crypt") still have 1 syllable
    return max(1, count)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --- Issue helpers ---------------------------------------------------------


def _issue(severity: str, category: str, rule_id: str, message: str, fix: str = "") -> dict[str, str]:
    return {"severity": severity, "category": category, "rule_id": rule_id, "message": message, "fix": fix}


def _compute_health_score(issues: list[dict[str, str]]) -> int:
    score = 100
    for issue in issues:
        penalty = _SEVERITY_PENALTY.get(issue.get("severity", "INFO"), -1)
        score += penalty
    return max(0, min(100, score))


def _cwv_status(metric: str, value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    thresholds = _CWV_THRESHOLDS.get(metric, {})
    good = thresholds.get("good")
    poor = thresholds.get("poor")
    if good is None and poor is None:
        return "UNKNOWN"
    if good is not None and value <= good:
        return "GOOD"
    if poor is not None and value > poor:
        return "POOR"
    return "NEEDS_IMPROVEMENT"


# --- Page audit ------------------------------------------------------------


def _audit_page_issues(parser: _SeoHtmlParser, body: str, url: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    title = parser.title.strip()
    desc = parser.meta.get("description", "")
    canonical = parser.canonical
    h1_count = len(parser.h1s)
    text = _strip_html(body)
    wc = _word_count(text)

    # Title checks
    if not title:
        issues.append(_issue("CRITICAL", "Core", "title-missing", "Title tag is missing", "Add a <title> tag (50-60 chars)"))
    elif len(title) < 15:
        issues.append(_issue("WARNING", "Core", "title-short", f"Title too short ({len(title)} chars)", "Expand to 50-60 chars"))
    elif len(title) > 65:
        issues.append(_issue("WARNING", "Core", "title-long", f"Title too long ({len(title)} chars)", "Shorten to 50-60 chars"))

    # Description checks
    if not desc:
        issues.append(_issue("CRITICAL", "Core", "desc-missing", "Meta description is missing", "Add meta description (150-160 chars)"))
    elif len(desc) < 50:
        issues.append(_issue("WARNING", "Core", "desc-short", f"Description too short ({len(desc)} chars)", "Expand to 150-160 chars"))
    elif len(desc) > 165:
        issues.append(_issue("WARNING", "Core", "desc-long", f"Description too long ({len(desc)} chars)", "Shorten to 150-160 chars"))

    # H1 checks
    if h1_count == 0:
        issues.append(_issue("CRITICAL", "Core", "h1-missing", "No H1 heading found", "Add exactly one H1 per page"))
    elif h1_count > 1:
        issues.append(_issue("WARNING", "Core", "h1-multiple", f"{h1_count} H1 headings found", "Use exactly one H1 per page"))

    # Canonical
    if not canonical:
        issues.append(_issue("WARNING", "Core", "canonical-missing", "Canonical tag is missing", "Add self-referencing rel=canonical"))

    # Word count
    if wc < 300:
        issues.append(_issue("WARNING", "Content", "thin-content", f"Low word count ({wc} words)", "Expand content to 300+ words minimum"))

    # Images without alt
    no_alt = [img for img in parser.images if not img.get("alt")]
    if no_alt:
        issues.append(_issue("WARNING", "Images", "img-alt-missing", f"{len(no_alt)} images without alt text", "Add descriptive alt text to all images"))

    # Images without dimensions
    no_dims = [img for img in parser.images if not img.get("width") or not img.get("height")]
    if no_dims:
        issues.append(_issue("INFO", "Images", "img-dimensions-missing", f"{len(no_dims)} images without width/height", "Add width/height to prevent CLS"))

    # Open Graph
    if not parser.og_tags.get("og:title"):
        issues.append(_issue("INFO", "Social", "og-title-missing", "og:title tag missing", "Add og:title for social sharing"))
    if not parser.og_tags.get("og:description"):
        issues.append(_issue("INFO", "Social", "og-desc-missing", "og:description tag missing", "Add og:description for social sharing"))

    # Robots meta
    robots_meta = parser.meta.get("robots", "").lower()
    if "noindex" in robots_meta:
        issues.append(_issue("INFO", "Core", "noindex", "Page has noindex directive", "Remove noindex if page should be indexed"))
    if "nofollow" in robots_meta:
        issues.append(_issue("INFO", "Core", "nofollow", "Page has nofollow directive", "Remove nofollow if links should be followed"))

    # Viewport (mobile-friendly)
    if not parser.meta.get("viewport"):
        issues.append(_issue("WARNING", "Mobile", "viewport-missing", "Viewport meta tag missing", "Add viewport meta for mobile-friendliness"))

    return issues


# --- Tool registration -----------------------------------------------------


def register_seo_tools(mcp: FastMCP) -> None:
    """Register SEO-related MCP tools."""

    @mcp.tool()
    def seo_audit_page(url: str) -> str:
        """Audit a single page for SEO issues (meta, headings, schema, canonical, images, content)."""
        err = _validate_url(url)
        if err:
            return err
        status, body, _ = _fetch(url)
        if status is None:
            return json.dumps({"ok": False, "error": f"Failed to fetch {url}"}, indent=2)
        if not body:
            return json.dumps({"ok": False, "error": "No HTML content returned", "status": status}, indent=2)
        parser = _parse_html(body)
        issues = _audit_page_issues(parser, body, url)
        score = _compute_health_score(issues)
        text = _strip_html(body)
        result: dict[str, Any] = {
            "ok": True,
            "url": url,
            "status": status,
            "score": score,
            "title": truncate(parser.title.strip(), 100),
            "description": truncate(parser.meta.get("description", ""), 200),
            "canonical": parser.canonical,
            "h1_count": len(parser.h1s),
            "h1s": parser.h1s[:5],
            "h2_count": len(parser.h2s),
            "word_count": _word_count(text),
            "content_hash": _content_hash(text[:5000]),
            "image_count": len(parser.images),
            "link_count": len(parser.links),
            "json_ld_count": len(parser.json_ld),
            "og_tags": {k: truncate(v, 100) for k, v in list(parser.og_tags.items())[:6]},
            "issues": issues,
            "issue_count": len(issues),
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_audit_site(start_url: str, max_pages: int = 100) -> str:
        """Crawl and audit a website (up to max_pages). Returns aggregate health score + per-page issues."""
        err = _validate_url(start_url)
        if err:
            return err
        max_pages = max(1, min(max_pages, _MAX_PAGES))
        parsed = urllib.parse.urlparse(start_url)
        base_domain = parsed.netloc
        visited: set[str] = set()
        queue: deque[str] = deque([start_url])
        all_issues: list[dict[str, str]] = []
        page_results: list[dict[str, Any]] = []

        while queue and len(visited) < max_pages:
            current = queue.popleft()
            normalized = _normalize_url(current)
            if normalized in visited:
                continue
            visited.add(normalized)
            status, body, _ = _fetch(normalized)
            if status is None or not body:
                continue
            parser = _parse_html(body)
            issues = _audit_page_issues(parser, body, normalized)
            all_issues.extend(issues)
            page_results.append({
                "url": normalized,
                "status": status,
                "score": _compute_health_score(issues),
                "title": truncate(parser.title.strip(), 80),
                "issue_count": len(issues),
            })
            # Enqueue same-domain links
            for link in parser.links:
                href = link.get("href", "")
                href_lower = href.lower()
                if not href or href_lower.startswith("#") or href_lower.startswith("mailto:") or href_lower.startswith("javascript:") or href_lower.startswith("tel:"):
                    continue
                absolute = urllib.parse.urljoin(normalized, href)
                link_parsed = urllib.parse.urlparse(absolute)
                if link_parsed.netloc == base_domain:
                    norm_link = _normalize_url(absolute)
                    if norm_link not in visited:
                        queue.append(norm_link)
            if len(queue) > max_pages * 2:
                queue = deque(list(queue)[:max_pages])

        overall_score = _compute_health_score(all_issues)
        critical = sum(1 for i in all_issues if i["severity"] == "CRITICAL")
        warnings = sum(1 for i in all_issues if i["severity"] == "WARNING")
        info = sum(1 for i in all_issues if i["severity"] == "INFO")
        result: dict[str, Any] = {
            "ok": True,
            "start_url": start_url,
            "pages_crawled": len(visited),
            "overall_score": overall_score,
            "total_issues": len(all_issues),
            "critical": critical,
            "warnings": warnings,
            "info": info,
            "pages": page_results[:50],
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_check_cwv(url: str, strategy: str = "mobile") -> str:
        """Check Core Web Vitals via Google PageSpeed Insights API (free, no key required)."""
        err = _validate_url(url)
        if err:
            return err
        if strategy not in _CWV_STRATEGIES:
            return json.dumps({"ok": False, "error": "strategy must be 'mobile' or 'desktop'"})
        api_url = (
            f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
            f"?url={urllib.parse.quote(url, safe='')}"
            f"&category=PERFORMANCE&strategy={strategy}"
        )
        ctx = ssl.create_default_context()
        req = urllib.request.Request(api_url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            return json.dumps({"ok": False, "error": f"PageSpeed API request failed: {exc!s}"}, indent=2)

        if not data.get("lighthouseResult"):
            return json.dumps({"ok": False, "error": "PageSpeed API returned no lighthouseResult (invalid URL or API error)"}, indent=2)
        audits = data.get("lighthouseResult", {}).get("audits", {})
        metrics: dict[str, Any] = {}
        for metric_key, audit_key in [("lcp", "largest-contentful-paint"), ("cls", "cumulative-layout-shift"), ("fcp", "first-contentful-paint"), ("ttfb", "server-response-time")]:
            audit = audits.get(audit_key, {})
            value = audit.get("numericValue")
            if value is not None:
                if metric_key in ("lcp", "fcp"):
                    value = round(value / 1000, 2)  # ms → s
                elif metric_key == "ttfb":
                    value = int(round(value, 0))  # ms as int
                else:
                    value = round(value, 3)
            metrics[metric_key] = {"value": value, "status": _cwv_status(metric_key, value)}

        # INP from CrUX if available
        crux = data.get("loadingExperience", {}).get("metrics", {})
        inp_data = crux.get("INTERACTION_TO_NEXT_PAINT", {})
        inp_value = None
        if inp_data:
            percentile = inp_data.get("percentile", 0)
            inp_value = int(round(percentile, 0))
        metrics["inp"] = {"value": inp_value, "status": _cwv_status("inp", inp_value)}

        overall_good = all(m["status"] == "GOOD" for m in metrics.values() if m["value"] is not None)
        result: dict[str, Any] = {
            "ok": True,
            "url": url,
            "strategy": strategy,
            "metrics": metrics,
            "all_good": overall_good,
            "note": "INP replaced FID in March 2024. FID is no longer a metric.",
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_validate_schema(url: str) -> str:
        """Extract and validate JSON-LD structured data from a page."""
        err = _validate_url(url)
        if err:
            return err
        status, body, _ = _fetch(url)
        if status is None or not body:
            return json.dumps({"ok": False, "error": f"Failed to fetch {url}"}, indent=2)
        parser = _parse_html(body)
        schemas: list[dict[str, Any]] = []
        for raw in parser.json_ld:
            try:
                parsed_json = json.loads(raw)
                if isinstance(parsed_json, list):
                    for item in parsed_json:
                        schemas.append(_classify_schema(item))
                else:
                    schemas.append(_classify_schema(parsed_json))
            except json.JSONDecodeError:
                schemas.append({"type": "INVALID_JSON", "status": "ERROR", "raw": truncate(raw, 200)})

        active_count = sum(1 for s in schemas if s.get("status") == "ACTIVE")
        deprecated_count = sum(1 for s in schemas if s.get("status") == "DEPRECATED")
        result: dict[str, Any] = {
            "ok": True,
            "url": url,
            "schema_count": len(schemas),
            "active": active_count,
            "deprecated": deprecated_count,
            "schemas": schemas,
            "note": "FAQPage retired May 2026 for rich results. HowTo deprecated Sept 2023.",
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_analyze_content(url: str) -> str:
        """Analyze page content for E-E-A-T signals, readability, word count, and citability."""
        err = _validate_url(url)
        if err:
            return err
        status, body, _ = _fetch(url)
        if status is None or not body:
            return json.dumps({"ok": False, "error": f"Failed to fetch {url}"}, indent=2)
        parser = _parse_html(body)
        text = _strip_html(body)
        wc = _word_count(text)
        flesch = round(_flesch_reading_ease(text), 1)

        # Citability: check for question-based headings
        question_headings = [h for h in parser.h2s + parser.h3s if h.endswith("?")]
        # Short paragraphs heuristic (split by sentence boundaries since _strip_html collapses whitespace)
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        # Group sentences into paragraphs of ~3 sentences each (heuristic)
        paragraphs: list[str] = []
        for i in range(0, len(sentences), 3):
            para = " ".join(sentences[i:i + 3])
            if para:
                paragraphs.append(para)
        if not paragraphs and text:
            paragraphs = [text]
        short_paragraphs = sum(1 for p in paragraphs if len(p.split()) <= 80)
        # Author/date signals
        has_author = bool(parser.og_tags.get("article:author") or "author" in parser.meta)
        has_date = bool(parser.og_tags.get("article:published_time") or "date" in text.lower()[:500])

        issues: list[dict[str, str]] = []
        if wc < 300:
            issues.append(_issue("WARNING", "Content", "thin-content", f"Low word count ({wc})", "Expand to 300+ words"))
        if flesch < 30 or flesch > 90:
            issues.append(_issue("INFO", "Content", "readability", f"Flesch score {flesch} (target 60-70)", "Simplify sentence structure"))
        if not question_headings:
            issues.append(_issue("INFO", "Content", "no-question-headings", "No question-based headings found", "Add question-based H2/H3 for AI citations"))
        if not has_author:
            issues.append(_issue("INFO", "E-E-A-T", "no-author", "No author signal detected", "Add author bio + credentials for E-E-A-T"))
        if not has_date:
            issues.append(_issue("INFO", "E-E-A-T", "no-date", "No publication date detected", "Add datePublished + dateModified"))

        result: dict[str, Any] = {
            "ok": True,
            "url": url,
            "word_count": wc,
            "flesch_reading_ease": flesch,
            "readability_target": "60-70",
            "question_headings": len(question_headings),
            "short_paragraphs": short_paragraphs,
            "total_paragraphs": len(paragraphs),
            "has_author_signal": has_author,
            "has_date_signal": has_date,
            "citability_score": min(100, (len(question_headings) * 20) + (20 if short_paragraphs > len(paragraphs) * 0.5 else 0) + (20 if has_author else 0) + (20 if has_date else 0) + (20 if 300 <= wc <= 2000 else 10)),
            "issues": issues,
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_check_geo(url: str) -> str:
        """Check AI Search / GEO readiness (AI crawler access, citability, semantic HTML, llms.txt)."""
        err = _validate_url(url)
        if err:
            return err
        status, body, _ = _fetch(url)
        if status is None or not body:
            return json.dumps({"ok": False, "error": f"Failed to fetch {url} or no content"}, indent=2)
        # Fetch robots.txt
        parsed_url = urllib.parse.urlparse(url)
        robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
        robots_status, robots_body, _ = _fetch(robots_url)
        robots_text = robots_body if robots_status and robots_body else ""

        # Check AI crawler access
        ai_crawler_access: dict[str, bool] = {}
        for crawler in _AI_CRAWLERS:
            pattern = re.compile(rf"User-agent:\s*{re.escape(crawler)}\s*\r?\nDisallow:\s*/", re.IGNORECASE)
            ai_crawler_access[crawler] = not bool(pattern.search(robots_text))

        # Check llms.txt
        llms_url = f"{parsed_url.scheme}://{parsed_url.netloc}/llms.txt"
        llms_status, llms_body, _ = _fetch(llms_url)
        has_llms_txt = bool(llms_status and llms_body)

        # Semantic HTML check
        parser = _parse_html(body) if body else _SeoHtmlParser()
        semantic_tags = ["article", "section", "nav", "aside", "header", "footer", "main"]
        has_semantic = any(f"<{tag}" in body.lower() for tag in semantic_tags) if body else False

        # Schema drift check (basic)
        has_schema = len(parser.json_ld) > 0

        geo_score = 0
        geo_score += 30 if all(ai_crawler_access.values()) else 15
        geo_score += 20 if has_semantic else 0
        geo_score += 20 if has_schema else 0
        geo_score += 15  # llms.txt optional, partial credit
        geo_score += 15 if has_llms_txt else 0

        result: dict[str, Any] = {
            "ok": True,
            "url": url,
            "geo_score": min(100, geo_score),
            "ai_crawler_access": ai_crawler_access,
            "has_llms_txt": has_llms_txt,
            "llms_txt_note": "llms.txt is NOT a Google ranking factor (primary-source). Optional.",
            "has_semantic_html": has_semantic,
            "has_schema": has_schema,
            "recommendation": "Allow AI crawlers, use semantic HTML, add question-based headings, cite primary sources.",
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_get_gsc_data(site_url: str, days: int = 28) -> str:
        """Get Google Search Console performance data. Requires GSC OAuth credentials configured externally."""
        err = _validate_url(site_url)
        if err:
            return err
        days = max(1, min(days, 90))
        # GSC API requires OAuth2 — return instructions if no credentials
        result: dict[str, Any] = {
            "ok": False,
            "error": "GSC API requires OAuth2 credentials",
            "site_url": site_url,
            "days": days,
            "instructions": textwrap.dedent("""\
                To use Google Search Console API:
                1. Create a Google Cloud project + enable Search Console API.
                2. Create OAuth2 credentials (service account or desktop app).
                3. Add your service account email as a user in GSC.
                4. Set credentials path in AIZEE_GSC_CREDENTIALS env var.
                5. Call this tool again with the configured credentials.
                API endpoint: https://www.searchconsole.googleapis.com/webmasters/v3/sites/{site}/searchAnalytics/query
                Free: 1200 queries per minute, official Google data.
            """),
        }
        return json.dumps(result, indent=2)

    @mcp.tool()
    def seo_find_opportunities(gsc_data: str) -> str:
        """Find SEO opportunities from GSC data: striking distance, low CTR, content decay, cannibalization."""
        err = validate_query(gsc_data)
        if err:
            return err
        try:
            data = json.loads(gsc_data)
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "gsc_data must be valid JSON"})

        rows = data.get("rows", [])
        if not isinstance(rows, list):
            return json.dumps({"ok": False, "error": "GSC data must contain a 'rows' array"})

        # Expected CTR curve by position (Advanced Web Ranking 2024 organic CTR study)
        expected_ctr = {1: 0.28, 2: 0.15, 3: 0.11, 4: 0.07, 5: 0.05, 6: 0.04, 7: 0.03, 8: 0.025, 9: 0.02, 10: 0.015}

        striking_distance: list[dict[str, Any]] = []
        low_ctr: list[dict[str, Any]] = []
        cannibalization: dict[str, set[str]] = {}

        for row in rows:
            query = row.get("query", "")
            page = row.get("page", "")
            clicks = row.get("clicks", 0)
            impressions = row.get("impressions", 0)
            ctr = row.get("ctr", 0)
            position = row.get("position", 0)

            # Striking distance: pos 4-20, ≥20 impressions
            if 4 <= position <= 20 and impressions >= 20:
                striking_distance.append({"query": query, "page": page, "position": round(position, 1), "impressions": impressions, "clicks": clicks})

            # Low CTR: actual < expected for position (skip invalid/missing position)
            if position <= 0:
                continue
            pos_int = max(1, min(10, int(position)))
            expected = expected_ctr.get(pos_int, 0.01)
            if ctr < expected * 0.5 and impressions >= 10:
                low_ctr.append({"query": query, "page": page, "position": round(position, 1), "ctr": round(ctr * 100, 2), "expected_ctr": round(expected * 100, 2), "impressions": impressions})

            # Cannibalization: multiple pages for same query (deduplicate)
            if query and page:
                cannibalization.setdefault(query, set()).add(page)

        cannibalization_issues = [
            {"query": q, "pages": sorted(pages)}
            for q, pages in cannibalization.items()
            if len(pages) > 1
        ]

        result: dict[str, Any] = {
            "ok": True,
            "total_queries": len(rows),
            "striking_distance": sorted(striking_distance, key=lambda x: x["impressions"], reverse=True)[:20],
            "striking_distance_count": len(striking_distance),
            "low_ctr": sorted(low_ctr, key=lambda x: x["impressions"], reverse=True)[:20],
            "low_ctr_count": len(low_ctr),
            "cannibalization": cannibalization_issues[:20],
            "cannibalization_count": len(cannibalization_issues),
            "note": "Content decay requires time-series data (compare 28-day periods). Provide two GSC datasets for decay analysis.",
        }
        return json.dumps(result, indent=2)


def _classify_schema(item: Any) -> dict[str, Any]:
    """Classify a JSON-LD item as active/deprecated/unknown. Handles @graph containers."""
    schema_type = ""
    if isinstance(item, dict):
        # Handle @graph containers (multiple schemas in one script)
        if "@graph" in item:
            graph = item["@graph"]
            if isinstance(graph, list):
                if not graph:
                    return {"type": "@graph", "status": "EMPTY", "count": 0}
                return {"type": "@graph", "status": "CONTAINER", "count": len(graph)}
            elif isinstance(graph, dict):
                # @graph as single object — classify the inner item
                return _classify_schema(graph)
        schema_type = item.get("@type", "")
        if isinstance(schema_type, list):
            schema_type = schema_type[0] if schema_type else ""
    if schema_type in _ACTIVE_SCHEMA_TYPES:
        status = "ACTIVE"
    elif schema_type in _DEPRECATED_SCHEMA_TYPES:
        status = "DEPRECATED"
    else:
        status = "UNKNOWN"
    return {"type": schema_type, "status": status, "data": truncate(json.dumps(item, default=str), 300)}
