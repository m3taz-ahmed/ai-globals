---
name: cli-first-access
description: Prefer native CLI tools over MCP servers for external platform access; doctor-probe before use (agent-reach pattern)
---
[SKILL] cli-first-access
[OBJ] Reach external platforms (video, social, repos, email) through their native CLI tools instead of standing up dedicated MCP servers. One skill + one doctor check replaces a whole server — same access, near-zero idle cost.
[RULES]
1. [REQ] Before adding a new MCP server, check whether a maintained CLI covers the same capability (e.g. `gh`, `yt-dlp`, `glab`, platform CLIs). If yes: use the CLI, don't add the server.
2. [REQ] Probe before use: run the CLI's health command (`--version`, `auth status`, `doctor`) — a real invocation, not just `which()`. Absence or auth failure = surface to the user, don't retry blindly.
3. [REQ] CLI invocations go through the runtime gate (`aizee check` / `Kernel.act`) like any other action; no side-effect calls without policy + budget clearance.
4. [REQ] Pass arguments as argv lists (no shell-string interpolation), never embed credentials in argv — use the CLI's own auth store (`gh auth login`, env vars, OS keyring).
5. [REQ] Parse structured output when the CLI offers it (`--json`, `--format`); fall back to text parsing only when no structured mode exists.
6. [REQ] Timeouts are mandatory on every external CLI call (network hangs kill agent loops).
7. [CMD] When a platform has no CLI and no existing plugin bridge, prefer adding a thin skill that documents the API + auth flow over building a new MCP server — servers cost a process slot per session forever.
8. [CMD] Keep the per-channel recipe (install, auth, probe, core commands) in one place: a `references/` file inside this skill's directory or the relevant tech-stack doc, so re-onboarding is a read not a rediscovery.
9. [PROHIBIT] Spawning long-lived daemons or background MCP processes for one-shot CLI-equivalent operations.
10. [PROHIBIT] Re-adding a disabled integration as an MCP server when the need is a single command — that was the bloat this skill replaces.
[NOTES]
- Adopted from github.com/Panniantong/agent-reach (channels do real health-probes on native CLIs; the agent invokes them directly).
- The disabled external MCP servers remain in `plugins/` (enabled: false) if a heavier bridge is ever genuinely needed; re-enable via `plugins.yaml`, not by re-spawning servers.
