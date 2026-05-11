# DevOps Standards & Infrastructure Resilience

> [!NOTE]
> **TRIGGER:** LOAD ON deployment planning, disaster recovery setup, infrastructure changes, platform engineering.
> **SCOPE:** Containerization (ref: `tech-stack/docker-containers.md`), Progressive Delivery, Chaos Engineering, Self-Healing Infrastructure, GitOps, IaC (ref: `tech-stack/terraform-iac.md`).

## 1. Deployment & Infrastructure

- Enforce a **Container-First** deployment strategy utilizing PHP 8.4/8.5 and FrankenPHP (Octane) for the backend.
- Mandate Infrastructure-as-Code (IaC) via Terraform for all resource provisioning. Terraform state must be stored remotely (S3 + DynamoDB locking).
- Ensure strict Environment Parity: Local Development ≈ Staging ≈ Production.
- Adopt **GitOps** principles: Git is the single source of truth for desired infrastructure state. Use tools like ArgoCD or Flux to reconcile actual state and detect configuration drift automatically.
- Embrace **Platform Engineering**: Provide developers with "golden path" templates (service scaffolds, Terraform modules, CI/CD workflows) to standardize delivery and reduce cognitive load.

## 2. Progressive Delivery & Release

- Implement **Progressive Delivery** as the default release strategy:
  - **Canary Deployments:** Route 1% → 5% → 25% → 100% of traffic to the new version, with automated health-check gates at each stage.
  - **Feature Flags:** Decouple deployment from release. Code is deployed "dark" (inactive) and activated via feature flags (e.g., LaunchDarkly, Unleash, or `Laravel Pennant`) when business conditions are met.
  - **Automated Rollback:** If error rates or latency exceed thresholds during canary promotion, trigger an immediate automated rollback without human intervention.
- Define clear Rollback Standard Operating Procedures (SOPs) for all deployment types.
- Ensure Database Migration Safety: destructive migrations (dropping columns/tables) are strictly prohibited in production without a verified backup and a multi-step deployment strategy (expand-then-contract pattern).

## 3. Self-Healing & Chaos Engineering

- Design systems with **closed-loop self-healing**: health check failures must trigger automatic remediation (pod restart, instance replacement, traffic rerouting) before human escalation.
- Implement **Chaos Engineering** as a continuous validation practice, not a one-time experiment:
  - Inject faults systematically (network latency, pod termination, disk pressure) to verify recovery paths.
  - Run game days quarterly to validate failover, autoscaling, and self-healing mechanisms under stress.
- Monitor infrastructure with deep observability (CloudWatch Container Insights, Performance Insights for Aurora) and automate anomaly-driven remediation via AIOps runbooks.

## 4. Security & Disaster Recovery

- **Eliminate long-lived secrets:** Adopt OIDC Keyless Authentication (e.g., GitHub Actions OIDC → AWS IAM Roles, EKS Pod Identities via IRSA) for all CI/CD and service-to-service authentication.
- Automate Secrets Rotation (e.g., rotating database credentials via AWS Secrets Manager with automatic propagation).
- Formulate a Disaster Recovery plan with defined RTO (Recovery Time Objective) and RPO (Recovery Point Objective) targets.
- Test backup and restore procedures quarterly via automated DR drills.
- Enforce **Policy-as-Code** (OPA/Kyverno) to validate infrastructure configurations against security and compliance baselines before deployment.

## 5. Hard Constraints

- NEVER deploy code directly via FTP or SSH; all deployments must be orchestrated by the CI/CD pipeline.
- NEVER run destructive database migrations in a single deployment step; always use the expand-then-contract pattern.
- NEVER store long-lived static secrets (AWS keys, tokens) in CI/CD pipelines; use OIDC keyless authentication exclusively.
- ALWAYS use immutable Docker image tags (e.g., Git SHA) in production deployments.
- ALWAYS validate infrastructure drift via GitOps reconciliation before deploying application code.

---

## ✅ DEVOPS STANDARDS COMPLIANCE CHECK (Mandatory)
- [ ] **Parity:** Does the Docker setup mirror the production Octane/FrankenPHP environment?
- [ ] **Safety:** Are destructive database migrations prevented using the expand-then-contract pattern?
- [ ] **Progressive Delivery:** Are canary deployments with automated health gates configured?
- [ ] **Self-Healing:** Are health check failures triggering automatic remediation before human escalation?
- [ ] **Chaos Engineering:** Are fault injection tests scheduled and executed quarterly?
- [ ] **Keyless Auth:** Is OIDC keyless authentication used for all CI/CD → cloud interactions?
- [ ] **GitOps:** Is infrastructure state reconciled from Git with automated drift detection?
