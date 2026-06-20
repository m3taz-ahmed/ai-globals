[WORKFLOW] ci-cd-standards
[OBJ] CI/CD Governance & Supply Chain Security.
[RULES]
1. [REQ] Branch Strategy `[GIT-03]`: `main` (prod), `develop` (staging). Merge requires ConvCommits, tests/lints pass, 1 approval.
2. [REQ] Pipeline Governance `[GIT-04]`: Auto-deploy `develop` to Staging. Run dependency audits in CI. OIDC keyless auth (no static tokens).
3. [REQ] Supply Chain Security (SLSA 3) `[GIT-05]`: Pin 3rd-party Actions by full commit SHA. Generate SBOM. Sign Docker images via Cosign.
