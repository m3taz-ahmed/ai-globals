[TECH] github-actions-ci
[OBJ] GitHub Actions CI Pipeline.
[RULES]
1. [REQ] Architecture: Separate PR (CI) and main (CD) workflows. Cache Composer/NPM.
2. [REQ] Gates: ESLint/PHPStan, 100% Pest/Playwright pass rate, Audit for CVEs, Trivy image scan.
3. [REQ] Deployment: Trigger on merge to `main`/`develop`. Manual approval for prod. Tag Docker with SHA.
4. [PROHIBIT] Security: NEVER hardcode AWS keys (Use OIDC). NEVER merge if CI fails.
