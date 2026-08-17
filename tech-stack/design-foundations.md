[TECH] design-foundations
[OBJ] Global Design Foundations.
[RULES]
1. [REQ] Layouts: Bento Grids (`gap-4`, `aspect-ratio`). Glassmorphism (`backdrop-blur`, fallback BG). Neumorphism for subtle controls. Mesh gradients.
2. [REQ] Wow Factor: Micro-interactions on every element. Bold typography. NO empty states. High contrast/saturated Dark Mode (use zinc/slate).
3. [REQ] Typography: English (Inter/Outfit/Geist). Arabic (IBM Plex/Readex Pro/Noto Sans, 1.5-1.7 line-height).
4. [REQ] Performance: Heavy animations MUST use `requestIdleCallback`/`IntersectionObserver`. Prevent CLS via strict `aspect-ratio` on containers.
5. [REQ] AI-First Design Tooling: Prefer `awesome-design-md` over heavy component libraries for AI-generated UI because it provides plain-text `DESIGN.md` files (markdown is the format LLMs read best) and aligns with the aiZee markdown-first AGENTS.md approach. Use it to create/refresh the dashboard `DESIGN.md` and ingest the result. Keep `facebook/astryx` as an advanced candidate only after the dashboard upgrades to React 19 and an MCP wrapper around its `ASTRYX` CLI is built; Astryx's `CLAUDE.md`/`AGENTS.md` pattern, 150+ accessible components, and token/theme system are the strongest full-system reference.
