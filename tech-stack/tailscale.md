[TECH] Tailscale 1.8x (WireGuard mesh)
[OBJ] Zero-config mesh VPN over WireGuard — the modern admin plane: private access to servers/services without opening inbound ports.
[RULES]
1. [REQ] Use as admin plane: install on every server → admin tooling (SSH, panels, DBs, monitoring) bound to tailscale0 or tailnet-only — close public ports entirely.
2. [REQ] `tailscale up --ssh` enables Tailscale SSH — SSH auth via tailnet identity + ACLs; then `PasswordAuthentication no` AND restrict public :22 (or drop it) — kills all bot noise.
3. [REQ] `tailscale serve` (tailnet-only) / `tailscale funnel` (public ingress) for exposing a local service ad-hoc — replaces port-forwarding/ngrok; funnel for webhooks/demos only, serve for internal.
4. [REQ] ACLs in admin console (tag-based): tag servers (`tag:prod`), grant user→tag SSH/serve rules; groups over individuals; `default-deny` posture on sensitive ports.
5. [REQ] Subnet routing/exit nodes: `--advertise-routes=192.168.x.0/24` for LAN access; `--advertise-exit-node` for full-tunnel egress; approve routes in admin console.
6. [REQ] Headless servers: `--auth-key` (tagged, reusable, ephemeral-off) for unattended installs; auth keys in secrets store, never in git.
7. [REQ] MagicDNS for names (`host.tail-xxx.ts.net`); HTTPS certs via `tailscale cert` on MagicDNS names — proper TLS inside the tailnet without public CA.
8. [REQ] Self-hosting control: Headscale if sovereignty required; stock Tailscale coordination is fine for most (data-plane is still WireGuard P2P/DTLS).
9. [PROHIBIT] Never use funnel for admin panels — tailnet-only (`serve`) or nothing.
10. [PROHIBIT] Never leave the host firewall thinking "LAN is safe" — tailnet traffic still deserves least-privilege ports.
11. [CMD] `tailscale status`, `tailscale ping <host>` (confirm P2P vs relay), `tailscale netcheck`, `tailscale serve status`, `tailscale ssh host`.
[COMPAT]
- Current: 1.8x line (2026); stable across Linux/Windows/macOS/containers.
- Docker: `tailscale/tailscale` sidecar w/ `TS_AUTHKEY` + `/dev/net/tun` — puts a container on the tailnet without host changes.
- Docs: https://tailscale.com/kb — Context7 `/tailscale/tailscale` when indexed.
[REFS]
- https://tailscale.com/kb
- https://github.com/juanfont/headscale (self-hosted control)
