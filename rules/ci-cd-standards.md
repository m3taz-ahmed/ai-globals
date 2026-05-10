# Tech-Stack: CI/CD Standards

> [!NOTE]
> **TRIGGER:** LOAD ON GitHub Actions configuration, deployment workflows, PR reviews, supply chain security.
> **SCOPE:** CI/CD governance, Branch strategies, Supply Chain Security (SLSA), OIDC, Automated pipelines.

## 1. Branch Strategy & PRs

- Adhere to a strict branch strategy: `main` (production), `develop` (staging), and `feature/*`, `bugfix/*`, `hotfix/*` branches.
- Enforce Pull Request (PR) requirements: all tests must pass, static analysis (linting) must be clean, and at least 1 peer approval is required before merging.
- Use Conventional Commits for clear history and automated changelog generation.
- Require PRs to include a **deployment risk assessment** tag (`risk:low`, `risk:medium`, `risk:high`) to gate manual approval requirements.

## 2. Pipeline Governance

- Mandate an automated deployment pipeline: push to `develop` deploys to Staging; merge to `main` triggers Production deployment (with manual approval gates for `risk:medium+`).
- Define a clear Hotfix workflow bypassing standard staging if absolutely necessary, but maintaining automated testing and requiring post-deployment verification.
- Integrate dependency audits (`composer audit`, `npm audit`) directly into the CI pipeline, failing the build on critical/high vulnerabilities.
- Enforce **Docker image scanning** (Trivy or Grype) in CI before pushing to ECR. Block deployments with critical CVEs.
- Generate a **Software Bill of Materials (SBOM)** for every production build using `syft` or `trivy sbom` to maintain a complete inventory of all dependencies.

## 3. Supply Chain Security (SLSA Level 3)

- **OIDC Keyless Authentication:** Eliminate all long-lived static secrets from CI/CD. Use GitHub Actions OIDC (`id-token: write`) to assume AWS IAM Roles via Workload Identity Federation. Configure trust policies scoped to specific repositories and branches.
- **Pin Actions by SHA:** NEVER use mutable tags (`@v4`) for third-party GitHub Actions. Always pin to full commit SHAs (`@b4ffde65...`) to prevent supply chain hijacking.
- **Artifact Signing:** Sign all production Docker images and release artifacts using **Sigstore (Cosign)** with keyless signing tied to the CI identity.
- **Provenance Attestation:** Generate SLSA provenance using `slsa-github-generator` for all production builds. Provenance must be verified at deployment time using `slsa-verifier` or equivalent policy engine.
- **Ephemeral Runners:** Use hosted, ephemeral build environments (GitHub-hosted runners or self-hosted with auto-scaling). Never build production artifacts on persistent, shared runners.

## 4. Least-Privilege Permissions

- Set `permissions: read-all` at the **workflow level** by default. Grant `write` access only to the specific jobs that require it (e.g., `packages: write` for publishing, `id-token: write` for OIDC).
- Use **GitHub Environments** to scope production secrets (deploy tokens, API keys) to the `production` environment, requiring manual approval and restricting access to the `main` branch only.
- Restrict `GITHUB_TOKEN` scope per job rather than per workflow to minimize blast radius from compromised steps.

## 5. Notifications & Telemetry

- Configure deployment notifications (Slack/Discord) for both successful and failed deployments, including the commit SHA, deployer, and environment.
- Track deployment markers in Sentry and Datadog to correlate performance metrics with releases.
- Establish a clear Rollback Standard Operating Procedure (SOP) that is accessible and practiced by the team.
- Track CI/CD pipeline metrics: build duration, failure rate, mean time to recovery (MTTR), and deployment frequency as key DORA metrics.

## 6. Hard Constraints

- NEVER bypass the CI pipeline for production deployments.
- NEVER merge a PR with failing CI checks or missing approvals (enforce via GitHub Branch Protection Rules).
- NEVER use mutable tags (`@v3`, `@latest`) for third-party GitHub Actions in production workflows.
- NEVER store long-lived static secrets (AWS keys, tokens) in GitHub Actions secrets; use OIDC keyless auth exclusively.
- ALWAYS ensure infrastructure changes via Terraform are applied and verified before application code deployments.
- ALWAYS generate and archive an SBOM for every production release.

---

## ✅ CI/CD STANDARDS COMPLIANCE CHECK (Mandatory)
- [ ] **Governance:** Are branch protection rules active enforcing tests and approvals?
- [ ] **Supply Chain:** Are all third-party Actions pinned by full commit SHA (not tags)?
- [ ] **OIDC:** Is keyless authentication configured for all CI/CD → cloud interactions?
- [ ] **SLSA:** Are provenance attestations generated and verified for production builds?
- [ ] **SBOM:** Is a Software Bill of Materials generated for every production release?
- [ ] **Scanning:** Are dependency and Docker image scans integrated and blocking on critical CVEs?
- [ ] **Least Privilege:** Is the `GITHUB_TOKEN` scoped to `read-all` by default with per-job overrides?
- [ ] **Workflow:** Is production deployment gated by a manual approval step with environment-scoped secrets?
