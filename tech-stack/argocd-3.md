[TECH] ArgoCD 3.5 (latest 3.5.2, Aug 2026)
[OBJ] GitOps continuous delivery for Kubernetes — impersonation (beta), Source Hydrator (beta), ApplicationSet preview apps, Helm 4.2.1, React 19 UI.
[RULES]
1. [REQ] Use impersonation (beta) — server-side operations now covered. Configure `--as` user for RBAC.
2. [REQ] Use Source Hydrator (beta) — dry-source integrity verification for GitOps workflows.
3. [REQ] Use ApplicationSet preview apps — auto-generate preview environments per PR.
4. [REQ] Use Helm 4.2.1 (bundled) — upgrade charts to Helm v4 format.
5. [REQ] Use React 19 UI — improved performance, better filtering, multi-cluster view.
6. [REQ] Use `ApplicationSet` for multi-environment deployments — matrix generators, git generators, cluster generators.
7. [REQ] Use `AppProject` for RBAC — restrict which repos, clusters, and namespaces each project can access.
8. [REQ] Use `syncPolicy.automated` for auto-sync, `syncPolicy.automated.prune` for auto-prune.
9. [REQ] Use `syncPolicy.automated.selfHeal` to prevent manual kubectl edits from drifting.
10. [REQ] Use `argocd app sync --dry-run` to validate before syncing.
11. [REQ] Use `argocd app diff` to compare live vs desired state.
12. [PROHIBIT] Never disable `selfHeal` in production — manual kubectl edits cause drift.
13. [PROHIBIT] Never use `--force` sync without understanding — deletes and recreates resources.
[COMPAT]
- ArgoCD 3.5.2 (released Aug 27 2026).
- v3.5.0 released Aug 4 2026.
- Helm 4.2.1 bundled.
- React 19 UI.
- Kubernetes 1.35+ recommended.
[REFS]
- https://github.com/argoproj/argo-cd/releases/tag/v3.5.2
- https://argo-cd.readthedocs.io/en/release-3.5/
