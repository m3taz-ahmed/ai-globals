# SEO Audit Rules
[REF] audit-rules
[OBJ] 251 SEO audit rules across 20 categories with weights (from SEOmator study + Claude SEO scoring).

## Category Weights (sum = 100%)
| Category | ID | Weight | Rule Count |
|----------|-----|--------|------------|
| Core | core | 12% | 19 |
| Performance | perf | 12% | 22 |
| Links | links | 8% | 19 |
| Images | images | 8% | 14 |
| Security | security | 8% | 16 |
| Technical SEO | technical | 7% | 13 |
| Crawlability | crawl | 5% | 18 |
| Structured Data | schema | 5% | 13 |
| JavaScript Rendering | js | 5% | 13 |
| Content | content | 5% | 17 |
| Accessibility | a11y | 4% | 12 |
| Social | social | 3% | 9 |
| E-E-A-T | eeat | 3% | 14 |
| URL Structure | url | 3% | 14 |
| Redirects | redirect | 3% | 8 |
| Mobile | mobile | 2% | 5 |
| Internationalization | i18n | 2% | 10 |
| HTML Validation | htmlval | 2% | 9 |
| AI/GEO Readiness | geo | 2% | 5 |
| Legal Compliance | legal | 1% | 1 |
| **TOTAL** | | **100%** | **251** |

## Rule Status Scoring
- pass = 100
- warn = 50
- fail = 0

## Two-Level Scoring
1. Category Score = Σ(statusScore × ruleWeight) / Σ(ruleWeight)
2. Overall Score = Σ(categoryScore × categoryWeight) / Σ(categoryWeight)

## Key Rules by Category

### Core (19 rules)
- Title present (50-60 chars)
- Description present (150-160 chars)
- H1 present (exactly one)
- Canonical present + self-referencing
- Title uniqueness across pages
- Description uniqueness
- Meta robots directives
- Open Graph tags
- Language declaration

### Performance (22 rules)
- LCP ≤2.5s
- INP ≤200ms
- CLS ≤0.1
- TTFB ≤800ms
- FCP ≤1.8s
- Compression enabled (gzip/brotli)
- Caching headers
- CSS/JS minification
- Render-blocking resources
- Image optimization

### AI/GEO Readiness (5 rules)
- Semantic HTML (article, section, nav, aside)
- Content structure (headings, lists, tables)
- AI bot access (robots.txt: GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended)
- llms.txt presence (optional, not ranking factor)
- Schema drift (JSON-LD vs visible content)

### JS Rendering (13 rules)
- Rendered title present
- Rendered description present
- Rendered H1 present
- Rendered canonical present
- Canonical mismatch (raw vs rendered)
- Noindex mismatch
- Title modified by JS
- Description modified by JS
- H1 modified by JS
- Content present without JS
- Links present without JS
- Critical JS not blocked
- SSR detection

## Exit Codes (for CI/CD)
- 0: Score ≥70 (passing)
- 1: Score <70 (failing)
- 2: Error occurred

## Output Formats
- Console: color-coded, letter grades (A-F)
- JSON: full audit result, CI/CD parsing
- HTML: standalone interactive report
- Markdown: GitHub-friendly, checklists
- LLM: token-efficient XML with nonce-stamped untrusted blocks (prompt-injection protection)
