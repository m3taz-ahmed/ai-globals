# SEO Health Score Algorithm
[REF] health-scoring
[OBJ] SEO Health Score algorithm (0-100) with category weights + penalty system.

## Health Score Formula
```
health_score = 100 - Σ(issue_penalty)
```
Floor: 0. Ceiling: 100.

## Issue Penalties
| Severity | Penalty |
|----------|---------|
| CRITICAL | -8 |
| WARNING | -3 |
| INFO | -1 |

## Category Weights (Claude SEO model)
| Category | Weight |
|----------|--------|
| Technical | 22% |
| Content | 23% |
| On-Page | 20% |
| Schema | 10% |
| Core Web Vitals | 10% |
| AI Search | 10% |
| Images | 5% |
| **TOTAL** | **100%** |

## Alternative: SEOmator 20-Category Model
See audit-rules.md for 251 rules across 20 categories with weights summing to 100%.

## Confidence-Weighted Aggregation
When aggregating multiple data sources:
| Source | Confidence |
|--------|-----------|
| Official API (GSC, PageSpeed) | 1.0 |
| Third-party (Moz, Bing) | 0.85 |
| Estimated | 0.70 |
| Crawled | 0.50 |

## Insufficient Data Gate
- Health score requires 4+ of 7 factors with data.
- If <4 factors have data: report "INSUFFICIENT DATA" instead of misleading numeric score.

## Content Scoring (per-page)
```
content_score = base(40) + title(15) + description(15) + h1(15) + wordcount(15) + schema(5) + canonical(5)
```
- Title (15-65 chars): +15 (partial: +5)
- Description (50-160 chars): +15 (partial: +5)
- Single H1: +15 (multiple H1: +5)
- Word count ≥300: +15 (≥100: +8)
- Has schema: +5
- Has canonical: +5
- Capped at 0-100.

## Expected CTR Curve (for opportunity detection)
| Position | Expected CTR |
|----------|-------------|
| 1 | 28% |
| 2 | 15% |
| 3 | 11% |
| 4 | 7% |
| 5 | 5% |
| 6 | 4% |
| 7 | 3% |
| 8 | 2.5% |
| 9 | 2% |
| 10 | 1.5% |

## Opportunity Detection
- Striking distance: Keywords ranking pos 4-20 with ≥20 impressions.
- Low CTR: Actual CTR < expected CTR for position.
- Content decay: ≥25% clicks drop (28-day vs prior 28-day).
- Cannibalization: Multiple pages ranking for same query.

## Python Implementation
```python
def compute_health_score(issues, pages_found):
    if pages_found == 0:
        return 0
    score = 100
    for issue in issues:
        if issue.severity == "CRITICAL":
            score -= 8
        elif issue.severity == "WARNING":
            score -= 3
        else:
            score -= 1
    return max(0, min(100, round(score)))
```
