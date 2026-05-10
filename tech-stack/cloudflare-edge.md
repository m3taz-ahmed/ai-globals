# Tech-Stack: Cloudflare Edge

> [!NOTE]
> **TRIGGER:** LOAD ON CDN configuration, DNS setup, security rules, edge computing.
> **SCOPE:** Cloudflare WAF, CDN, Workers, R2, Turnstile.

## 1. DNS & Caching
- Proxy DNS records through Cloudflare (orange cloud).
- Implement aggressive CDN Caching Rules via Cache-Control headers and custom page rules for static assets.
- Use Argo Smart Routing for latency reduction on dynamic API requests.

## 2. Security
- Enable Web Application Firewall (WAF) managed rules to block SQLi, XSS, and known CVEs.
- Configure Rate Limiting rules to protect login endpoints and expensive API routes.
- Enable DDoS protection and configure "Under Attack" mode triggers.
- Use Turnstile instead of reCAPTCHA for privacy-first bot protection.
- Enforce SSL in **Full (Strict)** mode, requiring origin certificates on the AWS ALB.

## 3. Edge Computing & Storage
- Deploy **Cloudflare Workers** for lightweight edge logic: A/B testing routing, geo-based redirects, or edge authentication.
- Utilize **R2 Storage** for S3-compatible object storage when avoiding AWS egress fees is a priority (e.g., serving heavy user-generated content).

## 4. Hard Constraints
- NEVER use "Flexible" SSL mode; traffic between Cloudflare and the origin must be encrypted.
- NEVER cache sensitive or user-specific HTML/JSON at the edge without strict authentication tokens in the cache key.
- ALWAYS test Page Rules and WAF changes in "Log" mode before enforcing "Block".

---

## ✅ CLOUDFLARE EDGE COMPLIANCE CHECK (Mandatory)
- [ ] **Encryption:** Is SSL configured to Full (Strict) mode?
- [ ] **Security:** Are WAF and Rate Limiting active on sensitive API endpoints?
- [ ] **Performance:** Are caching rules optimized to maximize the CDN hit ratio for static content?
