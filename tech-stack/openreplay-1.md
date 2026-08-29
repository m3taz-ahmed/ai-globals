[TECH] openreplay-1
[OBJ] Open-source session replay + product analytics (2026). MIT (openreplay/openreplay, ~13k★). SAFE TO COPY PATTERNS (MIT). Self-host free. aiZee cro_replay option (strong Arabic docs).
[DATA]
- Version/License: MIT. Self-host free (k8s/Docker). Cloud paid. MIT = safe to reuse replay/analytics patterns. Ships `README_AR` (strong Arabic support).
- Core Data Model: Project → Session (replay: DOM/network/console) → Event (click/input/error) → Funnel → Issue (crash/rage-click) → Heatmap → Performance (Web Vitals). Identifies via `setUserID`.
- Free-tier/Limits: Self-host unlimited sessions. Cloud free tier (limited sessions/mo). Tracker ~12KB. Ingestion self-hosted.
[API]
- Endpoint: `https://your.openreplay/api/`. Auth: project key (tracker) / admin token (API). Methods: `POST /ingest` (tracker), `GET /api/{project}/sessions`, `GET /api/{project}/funnels`. MCP app (`mcp_app`) ships.
- SDK: `openreplay` tracker (JS/web/mobile).
[CTX] Context7 ID: `websites/openreplay_openreplay` (real)
[RTL]
- RTL note: OpenReplay supports Arabic UI + ships **README_AR** (Arabic docs) — excellent MENA fit. Replay RTL pages correctly (DOM capture). Use for Arabic landing-page CRO (rage-clicks/heatmaps on RTL). MIT = safe pattern reuse for `cro_replay`.
[PROHIBIT] ⛔ MIT — keep attribution if reused. ⛔ Mask PII/sensitive inputs in replay (privacy). ⛔ Use self-host for data residency.
