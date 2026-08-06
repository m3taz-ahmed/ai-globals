[WORKFLOW] 19-incident-response
[TRIGGER] incident-response
[OBJ] Production incidents, outages, and emergency hotfixes.
[RULES]
1. [REQ] Classify: Assign SEV-1/2/3 severity; SEV-1 requires immediate communication.
2. [REQ] Communication: Notify affected stakeholders in a dedicated channel or on-call rotation.
3. [REQ] Contain: Stop the bleeding before diagnosis (revert, kill switch, rate limit, scale).
4. [REQ] Diagnose: Use `03-debugging.md` and telemetry; preserve audit trail and logs.
5. [REQ] Fix: Apply the smallest hotfix that restores service; no unrelated refactoring.
6. [REQ] Validate: Run smoke tests, health checks, and targeted test filters before declaring done.
7. [REQ] Post-incident: Schedule a blameless review and update runbooks/workflows.
8. [PROHIBIT] No hotfix without a rollback plan and a follow-up ticket for long-term remediation.
