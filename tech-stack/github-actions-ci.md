# Tech-Stack: GitHub Actions CI

> [!NOTE]
> **TRIGGER:** LOAD ON workflow automation, CI/CD pipeline setup.
> **SCOPE:** GitHub Actions, automated testing, deployment pipelines.

## 1. Pipeline Architecture
- Define distinct workflows for Pull Requests (CI) and main branch merges (CD).
- Utilize matrix builds to test across multiple PHP or Node.js versions if applicable.
- Configure dependency caching for Composer (`actions/cache`) and NPM to reduce build times.

## 2. Quality Gates & Security
- Run static analysis (ESLint, TypeScript `tsc`, PHPStan) on every PR.
- Execute Pest/PHPUnit test runners and Playwright E2E tests, requiring 100% pass rate.
- Implement dependency audits (`composer audit`, `npm audit`) and fail the build on critical vulnerabilities.
- Run Docker image scanning (e.g., Trivy) before pushing to ECR.
- Manage sensitive values using GitHub Secrets or AWS OIDC roles; never hardcode credentials.

## 3. Deployment Workflow
- Trigger deployments only on merges to `main` (for production) or `develop` (for staging).
- Enforce Environment Protection Rules in GitHub requiring manual approval before deploying to production.
- Automate Docker build, tag (with commit SHA), and push to AWS ECR.
- Automate database migrations in the deployment step, ensuring a rollback strategy exists.

## 4. Hard Constraints
- NEVER allow a PR to merge if CI checks fail.
- NEVER use long-lived AWS Access Keys in GitHub Secrets; ALWAYS use OpenID Connect (OIDC) to assume an IAM role.
- ALWAYS notify the team (via Slack/Discord integration) of deployment successes or failures.

---

## ✅ GITHUB ACTIONS CI COMPLIANCE CHECK (Mandatory)
- [ ] **Security:** Is OIDC used instead of hardcoded AWS keys?
- [ ] **Quality Gates:** Do all tests, linting, and security audits pass before merge?
- [ ] **Approvals:** Is manual approval required for production deployments?
