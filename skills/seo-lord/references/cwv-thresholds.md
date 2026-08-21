# Core Web Vitals Thresholds
[REF] cwv-thresholds
[OBJ] Core Web Vitals thresholds + measurement methods (2026, INP replaced FID March 2024).

## Core Web Vitals (Ranking Factors)

### LCP (Largest Contentful Paint)
- Good: ≤2.5s
- Needs Improvement: 2.5s - 4.0s
- Poor: >4.0s
- Measures: Loading performance of largest visible element.
- Optimize: Preload hero images, CDN, optimize images (WebP/AVIF), reduce TTFB, remove render-blocking resources.

### INP (Interaction to Next Paint) — replaced FID March 2024
- Good: ≤200ms
- Needs Improvement: 200ms - 500ms
- Poor: >500ms
- Measures: Responsiveness to user input (clicks, taps, keypresses).
- Optimize: Reduce JavaScript execution time, break up long tasks, use web workers, defer non-critical JS.
- ⛔ NEVER reference FID (First Input Delay). Replaced by INP.

### CLS (Cumulative Layout Shift)
- Good: ≤0.1
- Needs Improvement: 0.1 - 0.25
- Poor: >0.25
- Measures: Visual stability (layout shifts during loading).
- Optimize: Set width/height on images/videos, reserve space for ads/embeds, avoid inserting content above existing, use font-display: swap or optional.

## Additional Metrics (not ranking factors but important)

### TTFB (Time to First Byte)
- Good: ≤800ms
- Needs Improvement: 800ms - 1800ms
- Poor: >1800ms
- Optimize: CDN, server caching, database optimization, HTTP/2 or HTTP/3.

### FCP (First Contentful Paint)
- Good: ≤1.8s
- Needs Improvement: 1.8s - 3.0s
- Poor: >3.0s
- Optimize: Reduce TTFB, eliminate render-blocking resources, inline critical CSS, preload key resources.

### Speed Index
- Measures: How quickly content is visually displayed.
- Optimize: Optimize above-the-fold content, lazy load below-the-fold.

## Measurement Methods

### PageSpeed Insights API (free, recommended)
- Endpoint: GET https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed
- Params: url, category=PERFORMANCE, strategy=MOBILE|DESKTOP, key (optional)
- Returns: Lighthouse lab data + CrUX field data (28-day real user metrics).
- Rate limits: 25,000/day per project, 60 req/100s per key.
- Free, no billing required.

### Lighthouse CLI (free, local)
- Install: npm install -g lighthouse
- Run: lighthouse https://example.com --output=json --only-categories=performance
- Lab data only (no field data). Good for CI/CD.

### Lighthouse Node API (free, programmatic)
- For custom integrations. Same metrics as CLI.

### Playwright + PerformanceObserver (free, custom)
- For SPA rendering + CWV measurement.
- Inject PerformanceObserver script, collect LCP/CLS/TTFB/FCP.
- INP requires longer observation window (5-10s after load).

### Chrome UX Report (CrUX)
- Field data from real Chrome users.
- 28-day rolling window.
- Available via PageSpeed Insights API or BigQuery.

## Good Thresholds Check
```python
def is_vitals_good(vitals):
    lcp_good = vitals.lcp < 2.5 if vitals.lcp else True
    cls_good = vitals.cls < 0.1 if vitals.cls else True
    inp_good = vitals.inp < 200 if vitals.inp else True
    return lcp_good and cls_good and inp_good
```

## Mobile-First
- Google uses mobile-first indexing since 2019.
- Always measure CWV on mobile strategy first.
- Desktop CWV secondary but still important.
