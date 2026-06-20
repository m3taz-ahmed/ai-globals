[TECH] cloudflare-edge
[OBJ] Cloudflare Edge, CDN, and WAF.
[RULES]
1. [REQ] Routing: Proxy DNS (orange cloud). Use Argo Smart Routing.
2. [REQ] Security: WAF for SQLi/XSS. Rate Limit logins/APIs. "Under Attack" DDoS mode. Turnstile > reCAPTCHA. SSL Full (Strict).
3. [REQ] Edge Logic: Cloudflare Workers for A/B, geo-redirects. R2 Storage for S3-compatible assets (no egress fees).
4. [PROHIBIT] Hard Constraints: NEVER use Flexible SSL. NEVER cache user HTML without strict auth tokens in cache key.
