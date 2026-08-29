[TECH] automatisch-1
[OBJ] Open-source Zapier alternative / workflow automation (2026). AGPL-3.0 (automatisch/automatisch, ~14k★). Self-host free. Use as external service/plugin — DO NOT vendor core code.
[DATA]
- Version/License: AGPL-3.0. Self-host Docker = free unlimited (your infra). Cloud paid. aiZee marketing-automation option.
- Core Data Model: Workflow → Trigger (app event) → Step (action/filter/delay/code) → Connection (credential per app) → Execution (run log) → Flow (graph). Similar node model to n8n.
- Free-tier/Limits: Self-host unlimited (no paid walls on connectors). Cloud free tier limited. Community connectors; some paid-app credentials still need accounts.
[API]
- Self-hosted REST at `/api/`. Concepts: trigger/action nodes registry. aiZee `marketing-automation` wraps via plugin. No stable public REST doc — integrate through UI/export or plugin adapter pattern.
- SDK: Node connector SDK for custom apps.
[CTX] Context7 ID: `websites/automatisch_automatisch` (real)
[RTL]
- RTL note: Workflows can branch on locale (e.g. `language=ar`) to route Arabic users through RTL-aware email/CRM steps. Self-host keeps data in-region (Gulf). Use for Arabic lead-nurture journeys.
[PROHIBIT] ⛔ AGPL — never vendor/modify core for redistribution. ⛔ Use as service/plugin only. ⛔ No auto-execute without aiZee approval gate.
