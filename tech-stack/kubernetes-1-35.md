[TECH] Kubernetes 1.35 (latest 1.35.8, Aug 2026)
[OBJ] Container orchestration — 60 enhancements (17 stable, 19 beta, 22 alpha), stricter KYAML (beta), graduated core features.
[RULES]
1. [REQ] Kubernetes 1.34 EOL 27 Oct 2026 — upgrade to 1.35+ before EOL.
2. [REQ] Stricter KYAML (beta) — validate manifests with `kubectl apply --dry-run=server` before deploying; stricter schema enforcement.
3. [REQ] Review 60 enhancements: 17 stable (safe to use in prod), 19 beta (enable via feature gates), 22 alpha (experimental only).
4. [REQ] Use `kubectl` latest matching cluster version — version skew ±1 allowed.
5. [REQ] Use namespaces for isolation — never deploy workloads to `default` namespace in production.
6. [REQ] Use `Deployment` + `Service` for stateless apps; `StatefulSet` for stateful; `DaemonSet` for node-level.
7. [REQ] Use `HorizontalPodAutoscaler` + `VerticalPodAutoscaler` for scaling.
8. [REQ] Use `NetworkPolicy` to restrict pod-to-pod traffic — default deny, explicit allow.
9. [REQ] Use `PodSecurity Standards` (restricted) — never use PodSecurityPolicy (removed).
10. [REQ] Use `ConfigMap` + `Secret` for configuration — never bake config into images.
11. [REQ] Use `ReadinessProbe` + `LivenessProbe` + `StartupProbe` on all workloads.
12. [REQ] Use `resource requests` + `limits` on all containers — CPU + memory.
13. [REQ] Use `RBAC` (Role/ClusterRole/RoleBinding) — least privilege, never cluster-admin for service accounts.
14. [PROHIBIT] Never deploy to `default` namespace in production.
15. [PROHIBIT] Never use PodSecurityPolicy (removed) — use PodSecurity Standards.
16. [PROHIBIT] Never run without resource requests/limits.
17. [PROHIBIT] Never use alpha features in production without explicit approval.
18. [CMD] `kubectl apply -f manifest.yaml --dry-run=server` — validate with stricter KYAML.
19. [CMD] `kubectl rollout status deployment/<name>` — check rollout.
20. [CMD] `kubectl get pods -n <ns> -o wide` — inspect pods.
[COMPAT]
- Kubernetes 1.35.8: latest (Aug 2026).
- 1.34 EOL: 27 Oct 2026.
- KYAML stricter validation: beta.
- 60 enhancements: 17 stable, 19 beta, 22 alpha.
- kubectl version skew: ±1 from cluster version.
[REFS]
- https://kubernetes.io/docs/
- https://kubernetes.io/docs/reference/kubectl/
- https://kubernetes.io/docs/setup/release/notes/
