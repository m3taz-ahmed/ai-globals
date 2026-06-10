# DevOps Standards & Infrastructure Resilience
> [!NOTE]
> Trigger: deployment planning, disaster recovery setup, infrastructure changes, platform engineering.

## Infrastructure & Parity `[ENV-04]`
- **Container-First:** PHP 8.4/8.5 with FrankenPHP/Octane.
- **GitOps & IaC:** Terraform for remote state management. Reconcile drift automatically.
- **Golden Path:** Standardized Golden Path template scaffolds to minimize developer cognitive load.

## Progressive Delivery & Deployments `[GIT-04]`
- **Release Gating:** Canary deployments (1% → 5% → 25% → 100%) and feature flagging.
- **Rollback SOP:** Auto-rollback if error rates or latencies exceed defined thresholds during canaries.
- **Migration Safety:** No destructive migrations in a single step (use expand-then-contract pattern).

## Self-Healing & Chaos Engineering `[OBS-02]`
- **Self-Healing:** Closed-loop self-healing (automatic restart/re-routing on health check failure).
- **Chaos Testing:** Inject faults quarterly to validate recovery paths.
- **DR Drills:** Quarterly testing of backup/restore procedures with RTO/RPO targets.
