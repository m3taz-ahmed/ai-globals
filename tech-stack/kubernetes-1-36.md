[TECH] Kubernetes 1.36 (latest 1.36.4, Aug 2026)
[OBJ] Container orchestration — 70 enhancements (18 stable, 25 beta, 25 alpha). Fine-grained kubelet API auth (GA), User Namespaces (GA), Mutating Admission Policies with CEL (GA), Resource health status (beta), Workload Aware Scheduling (alpha). Codename: Haru.
[RULES]
1. [REQ] Use fine-grained kubelet API authorization (GA) — restrict kubelet API access per user/service account.
2. [REQ] Use User Namespaces (GA) — isolate container users from host users for security.
3. [REQ] Use Mutating Admission Policies with CEL (GA) — replace MutatingWebhookConfigurations with CEL-based policies for performance.
4. [REQ] Use Resource health status (beta) — `.status.allocatedResourcesStatus` for Pod hardware health reporting.
5. [REQ] Use Workload Aware Scheduling (alpha) — gang scheduling, job controller integration for distributed workloads.
6. [REQ] Use `kubectl` latest matching cluster version — version skew ±1 allowed.
7. [REQ] Use namespaces for isolation — never deploy workloads to `default` namespace in production.
8. [REQ] Use `Deployment` + `Service` for stateless apps; `StatefulSet` for stateful; `DaemonSet` for node-level.
9. [REQ] Use `HorizontalPodAutoscaler` + `VerticalPodAutoscaler` for scaling.
10. [REQ] Use `NetworkPolicy` to restrict pod-to-pod traffic — default deny, explicit allow.
11. [REQ] Use `PodSecurity Standards` (restricted) — never use PodSecurityPolicy (removed).
12. [REQ] Use `ConfigMap` + `Secret` for configuration — never bake config into images.
13. [REQ] Use `ReadinessProbe` + `LivenessProbe` + `StartupProbe` on all workloads.
14. [REQ] Use `resource requests` + `limits` on all containers — CPU + memory.
15. [REQ] Use `kubectl apply --dry-run=server` before deploying — validate manifests server-side.
16. [PROHIBIT] Never use PodSecurityPolicy — removed in 1.25+. Use PodSecurity Standards.
[COMPAT]
- Kubernetes 1.36.4 (released Aug 11 2026).
- v1.36.0 released Apr 22 2026 (Haru).
- v1.35 EOL: Feb 28 2027.
- v1.36 EOL: Jun 28 2027.
- 70 enhancements: 18 stable, 25 beta, 25 alpha.
[REFS]
- https://kubernetes.io/blog/2026/04/22/kubernetes-v1-36-release/
- https://kubernetes.io/releases/
- https://kubernetes.io/docs/
