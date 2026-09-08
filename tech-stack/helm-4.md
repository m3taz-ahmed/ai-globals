[TECH] Helm 4 (latest 4.2.4, Aug 2026)
[OBJ] Helm v4.x — current stable line. v3 in maintenance mode. Kubernetes package manager for templating, dependency management, and lifecycle management.
[RULES]
1. [REQ] Use Helm v4 for new charts — v3 is in maintenance mode only.
2. [REQ] Use `helm create <chart>` to scaffold new charts — standard structure (`Chart.yaml`, `values.yaml`, `templates/`).
3. [REQ] Use `helm dependency update` to manage chart dependencies — declared in `Chart.yaml` `dependencies`.
4. [REQ] Use `helm install --dry-run --debug` to validate templates before deployment.
5. [REQ] Use `helm upgrade --install --atomic --timeout 5m` for safe production upgrades — rolls back on failure.
6. [REQ] Use `helm rollback <release> <revision>` to revert to previous revision.
7. [REQ] Use `helm template` for rendering without deploying — CI/CD pipeline validation.
8. [REQ] Use `helm lint` to validate chart structure and syntax.
9. [REQ] Use `values.yaml` for default values, `values.production.yaml` for environment overrides: `helm upgrade -f values.yaml -f values.production.yaml`.
10. [REQ] Use `--set` for ad-hoc overrides, `--set-file` for sensitive values from files.
11. [REQ] Use `helm repo add` + `helm repo update` for remote chart repositories.
12. [REQ] Use OCI registries for chart distribution: `helm push oci://registry/charts`.
13. [PROHIBIT] Never use `helm install` without `--dry-run` in CI/CD — validate first.
14. [PROHIBIT] Never store secrets in `values.yaml` — use `--set` from secrets manager or Sealed Secrets.
[COMPAT]
- Helm 4.2.4 (released Aug 13 2026).
- v4 is current stable line.
- v3 in maintenance mode.
- Kubernetes 1.35+ recommended.
[REFS]
- https://github.com/helm/helm/releases/tag/v4.2.4
- https://helm.sh/docs/
