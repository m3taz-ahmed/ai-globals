# Tech-Stack: Sentry Tracking

> [!NOTE]
> **TRIGGER:** LOAD ON error monitoring, observability setup, performance tracking.
> **SCOPE:** Sentry SDKs for Laravel 12/13 and Next.js.

## 1. SDK Integration
- Integrate the Sentry SDK into both the Next.js frontend and the Laravel 12/13 backend.
- Upload Source Maps during the Next.js CI build process to ensure readable stack traces, then delete them from public assets.
- Configure Release Tracking by passing the Git SHA as the release version to correlate errors with specific deployments.

## 2. Context & Breadcrumbs
- Bind the authenticated user context (ID, email) to Sentry to track impacted users.
- Add custom context and tags (e.g., `tenant_id`, `subscription_tier`) to aid debugging.
- Ensure breadcrumbs (DB queries, HTTP requests, UI clicks) are actively recorded leading up to an exception.

## 3. Performance & Alerts
- Enable Sentry Performance Monitoring to track transactions and spans (e.g., slow database queries or API endpoints).
- Configure Issue Grouping rules to prevent alert fatigue from similar but distinct error messages.
- Set up Alert Rules to notify the engineering team via Slack/Discord for new issues or spikes in error rates.
- Implement the User Feedback widget on 500 error pages.

## 4. Hard Constraints
- NEVER log Personally Identifiable Information (PII) or sensitive data (passwords, credit cards) to Sentry. Use SDK data scrubbers.
- NEVER ignore Sentry alerts; every new issue must be assigned, resolved, or ignored explicitly.
- ALWAYS set a reasonable sample rate for performance transactions to control quota usage (e.g., `traces_sample_rate = 0.1`).

---

## ✅ SENTRY TRACKING COMPLIANCE CHECK (Mandatory)
- [ ] **Privacy:** Are data scrubbers configured to prevent PII leakage?
- [ ] **Correlation:** Is the release version and user context attached to all events?
- [ ] **Performance:** Is performance monitoring enabled with an appropriate sample rate?
