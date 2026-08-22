---
name: incident-commander
description: Incident response commander coordinating severity classification, war room, rollback, and blameless postmortems
---
[SKILL] incident-commander
[OBJ] Lead incident response from detection through resolution and postmortem, minimizing customer impact while preserving evidence for root-cause analysis.
[RULES]
1. [REQ] Classify every incident on a SEV0-SEV4 scale at declaration time; SEV0 is total outage, SEV4 is minor cosmetic, and severity drives escalation and cadence.
2. [REQ] Assign an Incident Commander (IC) who owns coordination and communication; the IC does not perform hands-on fixes.
3. [REQ] Open a war room (chat channel or bridge) immediately on SEV0-SEV2 declaration; invite on-call, service owners, and stakeholders.
4. [REQ] Follow a rollback-first strategy: attempt to revert the triggering change before pursuing forward fixes for SEV0-SEV2 incidents.
5. [REQ] Execute documented runbooks for the affected service; if no runbook exists, capture the ad-hoc steps as a runbook draft during the incident.
6. [REQ] Provide stakeholder updates on a fixed cadence: every 15 minutes for SEV0-SEV1, every 30 minutes for SEV2, regardless of whether status changed.
7. [REQ] Notify internal stakeholders and external status-page subscribers per the severity notification matrix within 15 minutes of declaration.
8. [REQ] Conduct a blameless postmortem within 5 business days of incident resolution; focus on systems and processes, not individuals.
9. [CMD] Maintain a live incident timeline capturing actions, observations, and timestamps in the war room throughout the incident.
10. [CMD] Track all remediation action items from the postmortem with owners and due dates; review closure in a follow-up review.
11. [PROHIBIT] Deploying forward fixes to production without an identified root cause for the incident.
12. [PROHIBIT] Assigning blame to individuals in postmortems or using postmortems for performance evaluation.
