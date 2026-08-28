---
name: web-quality
description: Web Quality Engineer — Lighthouse, Core Web Vitals, and holistic performance optimization.
---
[SKILL] web-quality
[OBJ] Achieve and sustain 90+ Lighthouse scores and green Core Web Vitals across all user journeys.
[RULES]
1. [REQ] LCP <2.5s (Largest Contentful Paint):
   - Preload the hero image: <link rel="preload" as="image" href="hero.webp">.
   - Optimize fonts: use font-display: swap or optional, preload critical font files.
   - Reduce TTFB with CDN and edge compute.
   - Eliminate render-blocking resources — inline critical CSS, defer non-critical CSS.
   - Use modern image formats (AVIF/WebP) with width and srcset attributes.
   - Target: LCP element loads within 2.5s at p75 on mobile 4G.

2. [REQ] INP <200ms (Interaction to Next Paint):
   - Reduce total JavaScript payload — code-split routes, tree-shake unused exports.
   - Break long tasks (>50ms) using scheduler.yield() or setTimeout chunking.
   - Defer non-critical JS with defer or dynamic import().
   - Minimize main-thread blocking from third-party scripts (analytics, chat widgets).
   - Use content-visibility: auto for off-screen sections to reduce rendering work.
   - Target: <200ms at p75.

3. [REQ] CLS <0.1 (Cumulative Layout Shift):
   - Set explicit width and height (or aspect-ratio CSS) on all images, videos, and embeds.
   - Reserve space for ads and dynamic content with min-height containers.
   - Avoid injecting DOM above existing content (banners, cookie bars pushed from top).
   - Ensure fonts are preloaded or use size-adjust to prevent FOIT/FOUT shift.
   - No layout shift from cookie banners — reserve space or use fixed positioning.
   - Target: <0.1 at p75.

4. [REQ] FCP <1.8s (First Contentful Paint):
   - Inline critical above-the-fold CSS in a <style> block in <head>.
   - Preload critical fonts: <link rel="preload" as="font" crossorigin>.
   - Minify and compress HTML (brotli or gzip).
   - Use HTTP/2 or HTTP/3 server push for critical assets.
   - Reduce server response time — optimize origin, enable caching.
   - Target: <1.8s at p75.

5. [REQ] TTFB <800ms (Time to First Byte):
   - Deploy behind a CDN with edge caching for static and cached dynamic content.
   - Use HTTP/2 or HTTP/3 with connection coalescing.
   - Cache HTML at the edge with stale-while-revalidate.
   - Optimize origin server — enable OPcache, reduce DB queries, use Redis for session/cache.
   - Redirect HTTP to HTTPS at edge, not origin (avoid double round-trip).
   - Target: <800ms at p75.

6. [REQ] Lighthouse SEO (Score 90+):
   - Unique descriptive <title> (<60 chars) and <meta name="description"> (<160 chars) per page.
   - Implement structured data (JSON-LD) for articles, products, breadcrumbs, FAQs.
   - Ensure mobile-friendly viewport meta tag.
   - Provide canonical URLs to prevent duplicate content indexing.
   - XML sitemap and robots.txt present and valid.
   - Internal links are crawlable — no JS-only navigation without SSR or fallback HTML.

7. [REQ] Lighthouse Best Practices (Score 90+):
   - Serve all content over HTTPS with valid TLS certificate — no mixed content.
   - Zero console errors in production build.
   - No deprecated or vulnerable JavaScript APIs (check with Snyk or npm audit).
   - Set appropriate Cache-Control and ETag headers for static assets.
   - Use rel="noopener" on target="_blank" links to prevent tab-nabbing.
   - Avoid geolocation, notifications, and device-orientation prompts on page load.

[CMD] Audit and measurement tools:
- Lighthouse CLI: `npx lighthouse <url> --output=html --output-path=./lighthouse-report.html --view --throttling-method=simulate`
- PageSpeed Insights API: `curl "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=<url>&strategy=mobile&category=performance&category=seo&category=best-practices&category=accessibility"`
- WebPageTest: `curl "https://www.webpagetest.org/runtest.php?url=<url>&k=<API_KEY>&f=json&location=Mobile.4G&runs=3"`
- Chrome UX Report (CrUX): query BigQuery for field-data CWV at p75 percentile.
- Lighthouse CI: `npx lhci autorun --collect.url=<url> --upload.target=temporary-public-storage`
[CMD] Context7: `/GoogleChrome/lighthouse` for Lighthouse configuration, custom audits, and CI integration.
