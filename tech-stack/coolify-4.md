[TECH] Coolify 4.x
[OBJ] Self-hosted PaaS (Heroku/Vercel alternative) — deploy apps/DBs/static sites from git or images to your own servers, single host or remote fleet over SSH.
[RULES]
1. [REQ] Install: official script on a fresh Linux host (Debian/Ubuntu LTS safest — non-LTS Ubuntu needs manual path); it installs Docker 24+, configures daemon (log rotation), creates `/data/coolify`, sets up SSH keys for server mgmt.
2. [REQ] Topology options: (a) all-in-one VPS (panel + apps), (b) panel on a protected host (e.g., Proxmox LXC) managing REMOTE VPS targets over SSH — pattern (b) keeps the public box clean and lets you close its SSH entirely with Tailscale.
3. [REQ] Access control: panel UI (:8000) behind VPN/Tailscale or IP allowlist + 2FA; NEVER public. The panel holds deploy keys + env secrets — treat as crown jewels.
4. [REQ] Deployments: git-push webhooks (GitHub/GitLab), Docker images, docker-compose stacks, one-click services (Postgres, Redis, S3-compatible, Uptime Kuma...); per-app env vars encrypted at rest; built-in Let's Encrypt via Traefik.
5. [REQ] Servers/remote targets: Coolify connects over SSH — target hosts need docker + the Coolify SSH key; validate `ssh root@target` reachability from the Coolify container before onboarding.
6. [REQ] Backups: enable per-database scheduled backups (S3 destination) INSIDE Coolify; panel state itself lives in `/data/coolify` — include it in host-level restic/borg backups.
7. [REQ] Upgrades: built-in update notifier (`Settings → Update`) or re-run the install script; snapshot host before major version jumps.
8. [REQ] Resource sizing: panel+DB ≈1GB RAM overhead; budget per-app separately; watch `docker stats` — a single greedy app can starve the panel.
9. [REQ] Logs/observability: per-app logs in UI; host-level node_exporter/netdata still required — Coolify is not host monitoring.
10. [PROHIBIT] Never expose :8000 publicly or run panel without MFA.
11. [PROHIBIT] Never treat Coolify's UI state as the only record — keep compose/env docs in the runbook; if the panel dies, you redeploy from git, not from memory.
12. [PROHIBIT] Never run it on the same box as a heavily-loaded app without resource limits (cgroups/docker limits).
[COMPAT]
- Latest: v4.3.x (4.3.9, Aug 2026); v4 is the current line (v3 EOL). Requires Docker 24+, supported distros (Ubuntu LTS, Debian, RHEL-family, SUSE, Arch, Alpine, ARM64).
- Inside Proxmox: run in a privileged LXC with docker-enabled settings (community script) or a VM.
- Docs: https://coolify.io/docs — Context7 `/coollabsio/coolify` when indexed.
[REFS]
- https://github.com/coollabsio/coolify
- https://coolify.io/docs
