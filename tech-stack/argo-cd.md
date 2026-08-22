[TECH] ArgoCD
[OBJ] Declarative GitOps continuous delivery tool for Kubernetes that syncs application state from Git repositories to target clusters.
[RULES]
1. [REQ] Define applications using the Application CRD with explicit `source.repoURL`, `targetRevision`, `destination.server`, and `destination.namespace`.
2. [REQ] Use AppProject CRDs to restrict which repos, clusters, and namespaces a project can deploy to; enforce RBAC per project via `rbac.csv` or OIDC groups.
3. [REQ] Enable auto-sync with `syncPolicy.automated.prune: true` and `selfHeal: true` for environments where manual drift correction is undesired.
4. [REQ] Use sync waves (sync-wave annotation `argocd.argoproj.io/sync-wave`) to order resource creation (e.g., CRDs before operators before workloads).
5. [REQ] Configure resource hooks (`PreSync`, `Sync`, `PostSync`, `SyncFail`) for database migrations, smoke tests, and rollback notifications.
6. [REQ] Define custom health checks via Lua scripts in `argocd-cm` ConfigMap for CRDs that lack native Kubernetes health status.
7. [REQ] Enable SSO (OIDC, SAML, or Dex) for the ArgoCD API/UI; map OIDC groups to ArgoCD RBAC roles via `argocd-rbac-cm`.
8. [REQ] Use ApplicationSet CRDs for multi-cluster and multi-environment deployments; leverage Git directory generators or cluster generators for scaling.
9. [REQ] Store ArgoCD admin password as a Kubernetes Secret (bcrypt hash); rotate periodically and disable the built-in admin in production.
10. [CMD] Use `argocd app sync <app>` with `--dry-run` to preview changes; use `argocd app diff` to compare live vs Git state.
11. [CMD] Use `argocd app wait <app> --sync --health` to block CI pipelines until sync completes and health passes.
12. [CMD] Use `argocd app history <app>` and `argocd app rollback <app> <history-id>` for manual rollbacks when auto-sync is disabled.
13. [PROHIBIT] Never store cluster credentials in plaintext — use secretRef or cloud IAM integration (e.g., GKE Workload Identity, AWS IRSA).
14. [PROHIBIT] Never disable `selfHeal` in production without a documented escalation reason — manual kubectl changes will persist undetected.
15. [PROHIBIT] Never deploy ArgoCD without network policies restricting the UI/API to internal traffic; expose only via Ingress with mTLS or SSO.
[COMPAT]
- v2.10.x: ApplicationSet GA, multi-source applications, OCI vault plugin
- v2.11.x: Progressive delivery with Argo Rollouts integration, Redis HA improvements
- v2.12.x: SSO group claiming improvements, kustomize remote base support
[REFS]
- https://argo-cd.readthedocs.io/
- https://argo-cd.readthedocs.io/en/stable/user-guide/application_sets/
- https://argo-cd.readthedocs.io/en/stable/operator-manual/appprojects/
- https://argo-cd.readthedocs.io/en/stable/user-guide/sync-waves/
