[TECH] Helm 3
[OBJ] Kubernetes package manager that templated charts into declarative manifests with release tracking, hooks, and OCI registry support.
[RULES]
1. [REQ] Define apiVersion: v2 in Chart.yaml; set name, version (SemVer 2.0), and appVersion explicitly for every chart.
2. [REQ] Use values.yaml for default configuration; override via `--values` files or `--set` flags; never hardcode environment-specific values in templates.
3. [REQ] Name all template files with a `.yaml` extension under `templates/`; use `{{ include }}` partials for shared helpers (names, labels, selectors).
4. [REQ] Scope releases with `--namespace` and set `namespace:` in templates via `.Release.Namespace`; never install into `default` namespace in production.
5. [REQ] Use chart hooks (pre-install, post-install, pre-upgrade, pre-delete) for init jobs and cleanup; annotate with `helm.sh/hook` and `helm.sh/hook-weight`.
6. [REQ] Declare subchart dependencies in Chart.yaml `dependencies:` block with version ranges and repository URLs; run `helm dependency update` before packaging.
7. [REQ] Use `helm template` to render and validate manifests before install; run `helm lint` to catch chart schema violations.
8. [REQ] Store charts in OCI registries (helm push oci://...) for immutable, signed distribution; use `helm pull oci://...` for retrieval.
9. [REQ] Use `helm upgrade --install --atomic --cleanup-on-fail` for safe rollouts; `--atomic` rolls back on failure automatically.
10. [CMD] Use `helmfile` for multi-chart, multi-environment declarative releases; define `helmfile.yaml` with repositories, releases, and values overrides.
11. [CMD] Use `helm diff upgrade <release> <chart>` to preview changes before applying; integrate into CI pipelines.
12. [CMD] Use `helm rollback <release> <revision>` to revert to a known-good release state.
13. [PROHIBIT] Never store secrets in values.yaml — use `--set-file` for external secret files or integrate External Secrets Operator / Sealed Secrets.
14. [PROHIBIT] Never use `helm install --wait` without `--timeout` — default 5m may mask hanging resources; always set an explicit timeout.
15. [PROHIBIT] Never reuse Tiller-based (Helm 2) patterns; Helm 3 is client-only with no in-cluster server component.
[COMPAT]
- v3.13.x: OCI support stable, post-renderer support, `--take-ownership` flag
- v3.14.x: Chart v2 schema validation improvements, `helm push` for OCI GA
- v3.15.x: `--ignore-not-found` for uninstall, improved `helm dependency build`
[REFS]
- https://helm.sh/docs/
- https://helm.sh/docs/topics/charts/
- https://helm.sh/docs/topics/registry/
- https://helmfile.readthedocs.io/
