---
name: qa-automation
description: QA Automation Engineer — 6 specialized E2E agents with Playwright, profile-based auth, and manifest-driven dispatch.
---
[SKILL] qa-automation
[OBJ] Comprehensive E2E test coverage through 6 specialized agents dispatched via a route-discovery workflow.
[RULES]
1. [REQ] smoke-tester Agent: Critical-path verification only.
   - Tests critical user journeys: login, core feature, checkout/submit, logout.
   - Must complete in <60s — acts as a deploy gate.
   - Any failure blocks deployment.
   - Maximum 10-15 test cases — no edge cases, no visual regression, no performance checks.
   - Fast feedback is the priority. Uses a single authenticated profile.

2. [REQ] ux-tester Agent: Full user-flow and visual regression testing.
   - Tests full user flows end-to-end including alternate paths and cancellation.
   - Visual regression via screenshot comparison (Playwright toHaveScreenshot with maxDiffPixelRatio).
   - Integrates axe-core accessibility checks (axe-playwright) on every page state.
   - Verifies copy, layout, and interaction states (hover, focus, active, disabled).
   - Reports UX inconsistencies with annotated screenshots.

3. [REQ] adversarial-tester Agent: Edge cases and error-state resilience.
   - Tests edge cases: empty inputs, max-length inputs, special characters, SQL/XSS strings.
   - Boundary values: 0, -1, MAX_INT, empty arrays, null, undefined.
   - Simulates network failures (Playwright route abort), 500 responses, and slow 3G.
   - Tests concurrent form submission, double-click, and back-button behavior.
   - Verifies error messages are user-friendly and no stack traces leak to the client.

4. [REQ] performance-tester Agent: Lighthouse and Core Web Vitals measurement.
   - Runs Lighthouse audit on key pages via Playwright (lighthouse-playwright integration).
   - Measures Core Web Vitals (LCP, INP, CLS, FCP) using Playwright trace and CDP session.
   - Performs basic load testing with concurrent browser contexts (10-50 parallel).
   - Compares results against thresholds: LCP <2.5s, INP <200ms, CLS <0.1.
   - Reports regressions with flamegraph traces and Lighthouse HTML reports.

5. [REQ] mobile-tester Agent: Responsive, touch, and viewport validation.
   - Tests responsive layouts at standard breakpoints: 320, 375, 768, 1024, 1440px.
   - Verifies touch interactions (tap, long-press, swipe) using Playwright touch events.
   - Checks viewport meta tag and confirms no horizontal scroll at any breakpoint.
   - Tests device pixel ratio (2x, 3x) for image quality.
   - Emulates mobile devices (iPhone 13, Pixel 5, iPad) via Playwright device descriptors.
   - Verifies 44x44px touch target compliance.

6. [REQ] multi-user-tester Agent: Auth flows and data isolation.
   - Tests authentication flows: login, logout, session expiry, token refresh.
   - Tests concurrent sessions across multiple browser contexts with different users.
   - Verifies data isolation — user A cannot see user B's data.
   - Tests role-based access control (admin vs user vs guest).
   - Handles 2FA manually (pause for code entry or pre-seeded TOTP secret).
   - Tests OAuth flows with profile-based persistence.

7. [REQ] Workflow — Discover Routes:
   - Scan the application for all routes by parsing the router config (Next.js app dir, React Router, Laravel web.php).
   - Include sitemap.xml routes.
   - Categorize routes by type: public, auth-required, admin, API.
   - Output: route manifest JSON with route, method, auth-level, and suggested agent.

8. [REQ] Workflow — Generate Test Manifest:
   - Public routes → smoke + ux + mobile.
   - Auth routes → smoke + ux + multi-user + mobile.
   - Admin routes → smoke + multi-user + adversarial.
   - API routes → adversarial + performance.
   - Output: test-manifest.json mapping agent to array of routes.

9. [REQ] Workflow — Dispatch Agents:
   - Run independent agents in parallel (smoke + mobile on different routes).
   - Run dependent agents sequentially (smoke must pass before ux on same route).
   - Each agent writes results to .playwright/results/<agent>/<route>.json.
   - Use Playwright projects to shard by agent.
   - Maximum 4 parallel agents to avoid resource contention.

10. [REQ] Workflow — Collect & Report:
    - Aggregate all agent results into a unified report.
    - Failures include route, agent, error, screenshot, and trace path.
    - Generate HTML report via Playwright reporter with custom annotations.
    - Exit code 1 if any CRITICAL or HIGH severity failure.
    - Report saved to .playwright/reports/report.html.

11. [REQ] Profile-Based Auth:
    - Save authenticated browser states to .playwright/profiles/<role>.json using Playwright storageState.
    - OAuth and 2FA flows handled manually — test pauses, developer completes auth in headed browser, state is saved.
    - Profiles are refreshed on expiry (re-run auth flow, overwrite saved state).
    - Never store credentials in test code — use environment variables or .playwright/.env.
    - Profiles directory is gitignored.

[CMD] Playwright CLI:
- Setup: `npx playwright init`
- Run all: `npx playwright test`
- Run by agent/project: `npx playwright test --project=smoke`
- Shard: `npx playwright test --shard=1/4`
- Record: `npx playwright codegen <url>`
- View report: `npx playwright show-report`
- Update visual baselines: `npx playwright test --update-snapshots`
- Config in playwright.config.ts with projects per agent.
[CMD] Context7: `/microsoft/playwright` for API docs, fixture patterns, locator strategies, and authentication state management.
