[TECH] Caddy 2.11
[OBJ] Go-based web server/reverse proxy with automatic HTTPS — simplest path to TLS-secured sites; default proxy for small/medium deployments.
[RULES]
1. [REQ] Config: Caddyfile for humans (`app.example.com { reverse_proxy 127.0.0.1:3000 }`), JSON/`caddy-api` for automation; `caddy fmt --overwrite` to normalize; `caddy adapt` to inspect generated JSON.
2. [REQ] Auto-HTTPS: public domain in the site address → Caddy obtains+renews Let's Encrypt/ZeroSSL automatically; needs ports 80+443 reachable; internal sites: `tls internal` (local CA).
3. [REQ] Ops: run via systemd unit (`caddy.service`, config `/etc/caddy/Caddyfile`); `caddy reload --config` for zero-downtime; admin API on localhost:2019 by default — never expose.
4. [REQ] Proxy extras: WebSocket/gRPC work automatically (no upgrade headers needed); `header_up`/`header_down` for header control; `handle`/`route`/`respond`/`try_files`/`file_server` for static + fallback combos.
5. [REQ] Logging: `log` directive → JSON to `/var/log/caddy/`; `caddy` user needs write perms; journalctl -u caddy for service logs.
6. [REQ] When NOT Caddy: extreme config control/exotic modules → nginx; docker-label-driven dynamic routing → Traefik; but for 80% of sites Caddy wins on ops simplicity.
7. [REQ] Docker: `caddy:2-alpine` image; mount Caddyfile + `caddy_data`+`caddy_config` volumes (cert persistence!); expose 80/443 only.
8. [PROHIBIT] Never run Caddyfile + JSON config concurrently — pick one source of truth.
9. [PROHIBIT] Never expose :2019 admin endpoint to network.
10. [PROHIBIT] Don't disable HTTPS (`auto_https off`) on public hosts except under a TLS-terminating LB.
[COMPAT]
- Latest: 2.11.x (2.11.4, Jun 2026). Plugins via xcaddy builds (e.g., Cloudflare DNS module for DNS-01).
- Docs: https://caddyserver.com/docs — Context7 `/caddyserver/caddy`.
[REFS]
- https://caddyserver.com/docs/caddyfile
- https://github.com/caddyserver/caddy
