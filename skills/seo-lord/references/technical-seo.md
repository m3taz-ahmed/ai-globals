# Technical SEO Checks
[REF] technical-seo
[OBJ] 9 categories of technical SEO checks grounded in Google Search Essentials.

## 1. Crawlability
- robots.txt: Parse + validate. Check Disallow rules. Reference sitemap. AI crawler rules (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot, Google-Agent).
- Sitemaps: XML at /sitemap.xml. Max 50K URLs/file, 50MB/file. Sitemap index for large sites. Cross-reference with crawl: flag missing URLs. Submit to GSC + Bing + IndexNow.
- noindex: Check meta robots + X-Robots-Tag. Flag noindexed pages in sitemap.
- Crawl depth: Max 3 clicks from homepage. Orphan page detection (zero inlinks).
- Googlebot fetch limits: 2MB HTML, 64MB PDF.

## 2. Indexability
- Canonicals: Self-referencing on every indexable page. Detect canonical chains, mismatches.
- Duplicates: Content hash (SHA-256 of stripped body text). Duplicate title/description detection.
- Thin content: <60 content score. Word count floors (homepage 500, blog 1500, product 300+).
- Pagination: rel="next"/rel="prev" or canonical to view-all. Faceted nav: noindex duplicate facets.
- hreflang: Correct codes (en-US not en-us), return tags, x-default. Content parity.

## 3. Security
- HTTPS: Redirect HTTP→HTTPS. HSTS (max-age=31536000; includeSubDomains; preload).
- CSP: Content-Security-Policy header. Report-only for testing.
- X-Frame-Options: DENY or SAMEORIGIN. Prevents clickjacking.
- X-Content-Type-Options: nosniff.
- Mixed content: HTTP resources on HTTPS page. ⛔ block all.
- Back-button hijacking detection.

## 4. URL Structure
- Clean URLs: kebab-case, <75 chars, max 3 levels deep.
- ⛔ underscores, uppercase, session IDs, >3 query params, file extensions (except legacy).
- Trailing slashes: consistent (either always or never).
- Redirects: 301/308 permanent, 302/307 temporary. Max 1 hop (3 absolute).

## 5. Mobile
- Responsive design + viewport meta.
- Touch targets ≥48px. Font size ≥16px.
- Content parity (mobile-first indexing since 2019).
- No horizontal scroll. No interstitials.

## 6. Core Web Vitals (see cwv-thresholds.md)
- LCP ≤2.5s, INP ≤200ms, CLS ≤0.1. Mobile-first.
- INP replaced FID March 2024. ⛔ NEVER reference FID.

## 7. JavaScript Rendering
- SPA detection: empty <div id="root">, single bundle script.
- Raw vs rendered DOM diff: title, description, canonical, H1, content, links.
- SSR preferred for SEO-critical pages. CSR = risk.
- December 2025 JS SEO guidance: Google renders JS but rendering queue has delays.

## 8. IndexNow
- Submit URLs to Bing/Yandex/Naver via IndexNow API.
- Batch submission. Key in robots.txt or root.
- Instant indexing for new/updated URLs.

## 9. Agent-Friendly Pages (2026)
- Accessibility tree scoring. Semantic HTML (article, section, nav, aside, header, footer, main).
- Lighthouse Agentic Browsing category.
- AI bot access via robots.txt (GPTBot, ClaudeBot, PerplexityBot).
- llms.txt: optional, Google ignores for rankings (primary-source evidence).

## Crawl Budget Analysis (from server logs)
- Bot signatures: 90+ patterns including AI crawlers (GPTBot, ChatGPT-User, OpenAI SearchBot, ClaudeBot, PerplexityBot, GrokBot, CCBot, Google-Extended).
- Bot verification: Official IP ranges (Google: googlebot.com DNS verification, Bing: bing.com/toolbox/bingbot.json, OpenAI: 3 separate ranges for SearchBot/ChatGPT-User/GPTBot).
- Verified vs unverified: Distinguish real crawlers from impersonators.
- Status code distribution per bot (success/redirect/client_error/server_error).
- URL pattern segmentation with custom taxonomies.
- File type detection (images, videos, audio, documents, fonts).
- Streaming parser: line-by-line, no full file load. Regex for Nginx/Apache combined log format.
