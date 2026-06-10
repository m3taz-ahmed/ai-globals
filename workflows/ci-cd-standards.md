# CI/CD Governance & Supply Chain Security
> [!NOTE]
> Trigger: GitHub Actions configuration, deployment workflows, PR reviews, supply chain security.

## Branch Strategy & PRs `[GIT-03]`
- **Branches:** `main` (production), `develop` (staging), `feature/*`, `bugfix/*`, `hotfix/*`.
- **Merge Requirements:** ConvCommits, tests pass, lints pass, 1 peer approval.
- **Risk Tagging:** Tag PRs with risk profile (`risk:low/medium/high`) to gate production manual approvals.

## Pipeline Governance `[GIT-04]`
- **Auto-Deploy:** Merge to `develop` deploys to Staging; merge to `main` gates Production.
- **Auditing:** Run dependency audits (`composer/npm audit`) in CI; fail on high/critical CVEs.
- **Secrets:** Use OIDC keyless authentication for AWS/EKS Workload Identity Federation. ⛔ static tokens.

## Supply Chain Security (SLSA 3) `[GIT-05]`
- **Pin Actions:** Pin third-party GitHub Actions by full commit SHA. ⛔ mutable tags.
- **SBOM:** Generate Software Bill of Materials natively using Docker BuildKit.
- **Artifact Verification:** Sign Docker images using Cosign; generate SLSA provenance.
- **Least-Privilege:** Scoped `GITHUB_TOKEN` permissions (`read-all` by default).
