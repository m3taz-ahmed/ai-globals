[TECH] Kubernetes
[OBJ] Container orchestration platform for automating deployment, scaling, and management of containerized applications across clusters.
[RULES]
1. [REQ] Define resource requests and limits (CPU/memory) on every pod spec to prevent resource starvation and enable scheduler bin-packing.
2. [REQ] Use Deployments for stateless workloads with replicas >= 2 and rollingUpdate strategy with maxSurge and maxUnavailable set explicitly.
3. [REQ] Use Namespaces to isolate environments (dev/staging/prod) and teams; apply ResourceQuotas and LimitRanges per namespace.
4. [REQ] Store sensitive data (passwords, tokens, certs) in Secrets, never ConfigMaps; enable encryption at rest for the etcd Secret store.
5. [REQ] Configure liveness, readiness, and startup probes on all pods; use readiness probes for traffic gating via Services.
6. [REQ] Use Ingress with TLS termination and valid certificates; prefer ingress-nginx or Traefik with rate-limiting and request-body-size annotations.
7. [REQ] Enable RBAC with least-privilege Roles/ClusterRoles bound via RoleBindings; avoid cluster-admin for service accounts.
8. [REQ] Use HorizontalPodAutoscaler (HPA) with custom or external metrics for workloads with variable load; ensure metrics-server is deployed.
9. [REQ] Pin container image tags to immutable digests (imagePullPolicy: IfNotPresent) rather than mutable tags like `latest`.
10. [REQ] Use PodDisruptionBudgets (PDB) with minAvailable or maxUnavailable to maintain quorum during voluntary disruptions (node drains, upgrades).
11. [CMD] Use `kubectl apply -f` for declarative management; avoid `kubectl create` for resources under GitOps control.
12. [CMD] Use `kubectl rollout status deployment/<name>` and `kubectl rollout undo deployment/<name>` to verify and roll back deployments.
13. [CMD] Use Helm charts for templated multi-resource deployments; run `helm lint` and `helm template` before `helm install/upgrade`.
14. [PROHIBIT] Never use `:latest` image tag in production — it breaks reproducibility and rollback.
15. [PROHIBIT] Never run pods as root or with privileged securityContext in production; set runAsNonRoot: true and drop ALL capabilities.
[COMPAT]
- v1.29.x: LTS, stable Gateway API, native sidecar containers (KEP-753)
- v1.30.x: AppArmor GA, kubelet user namespace support beta
- v1.31.x: KMSv2 GA, structured authorization config alpha
[REFS]
- https://kubernetes.io/docs/home/
- https://kubernetes.io/docs/reference/kubectl/
- https://helm.sh/docs/
- https://kubernetes.io/docs/concepts/configuration/secret/
