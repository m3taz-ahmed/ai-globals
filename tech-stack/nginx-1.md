[TECH] nginx 1.30 (stable) / 1.31 (mainline)
[OBJ] High-performance reverse proxy, web server, load balancer — the default edge for Linux servers.
[RULES]
1. [REQ] Structure: `sites-available`/`sites-enabled` (Debian) or `conf.d/` (RHEL); one server block per app; `nginx -t` before EVERY reload; `systemctl reload nginx` (not restart) to apply.
2. [REQ] Reverse proxy core: `proxy_pass http://127.0.0.1:PORT;` + `proxy_set_header Host $host; X-Real-IP $remote_addr; X-Forwarded-For $proxy_add_x_forwarded_for; X-Forwarded-Proto $scheme;` + timeouts (`proxy_read_timeout`, `proxy_connect_timeout`) + `client_max_body_size` for uploads.
3. [REQ] WebSocket upgrades: `proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection "upgrade";` on the location that needs it — not global.
4. [REQ] TLS: ACME-managed certs (certbot/acme.sh/Caddy-adjacent automation); strong suite `ssl_protocols TLSv1.2 TLSv1.3;`, `ssl_session_cache shared:SSL:10m;`, OCSP stapling, HSTS only after verified; redirect `listen 80` → 443.
5. [REQ] Security headers: `add_header X-Content-Type-Options nosniff; X-Frame-Options SAMEORIGIN; Referrer-Policy strict-origin-when-cross-origin;` (+ CSP per app); `server_tokens off;`; rate-limit login endpoints via `limit_req_zone`.
6. [REQ] Static/media: `root`/`alias` with `try_files`; long `expires` + `immutable` for hashed assets; `sendfile`/`tcp_nopush`/`tcp_nodelay` on; gzip/brotli for text types only (never compress images/video).
7. [REQ] Load balance/failover: `upstream { server a:3000; server b:3000; }` + `least_conn` when needed; health via passive `max_fails`/`fail_timeout` (open-source) — real health checks need nginx-plus or a sidecar pattern.
8. [REQ] Logging: `access_log` json format for ingestion (`log_format json escape=json ...`); separate access/error per vhost; logrotate via distro unit (`/etc/logrotate.d/nginx` exists by default — verify).
9. [REQ] Performance: `worker_processes auto;`, `worker_connections 1024+`, `keepalive` upstream connections, buffer tuning only with measurement (defaults fit 95% of cases).
10. [PROHIBIT] Never `if` inside `location` for rewrites — use `try_files`/`return`/`map`; `if` in location is a known footgun.
11. [PROHIBIT] Never `proxy_pass` to a public/unauthenticated upstream (docker socket, internal admin) without allowlist.
12. [PROHIBIT] Never skip `nginx -t` — a failed reload kills all sites.
13. [PROHIBIT] Never serve `.env`/`*.git`/backup files — explicit `location ~ /\.` deny.
[COMPAT]
- Stable 1.30.4 (Jul 2026); mainline 1.31.5 adds control API, predicate locations, ngx_http_json_module. Production = stable branch.
- CVE batch fixed through 1.30.4 — patch level matters; keep updated via distro or nginx.org repo.
- Docs: https://nginx.org/en/docs/ — Context7 `/nginx/nginx`.
[REFS]
- https://nginx.org/en/docs/
- https://github.com/nginx/nginx (release notes)
