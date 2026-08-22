[TECH] render
[OBJ] Render platform — web services, background workers, cron jobs, static sites, disks, private spaces, blue-green deploys, Docker.
[RULES]
1. [REQ] Use web services for HTTP applications (Node.js, Python, Ruby, Go, Rust); configure via `render.yaml` Blueprint or the Dashboard — set build command, start command, and health check path; every push to the connected branch triggers a deploy.
2. [REQ] Use background workers for non-HTTP long-running processes (queue consumers, schedulers); workers do not expose a port and scale horizontally — never use web services for queue consumers as they will be killed if no port is bound.
3. [REQ] Use cron jobs for scheduled tasks via `render.yaml` with `schedule` (crontab syntax); each cron job is a one-off command that runs and exits — never use long-running workers for scheduled tasks; use a dedicated cron service.
4. [REQ] Use static sites for SPA and static asset hosting; static sites are free-tier eligible and served via CDN — configure publish directory and redirects/headers in `render.yaml` or `static.json`; never deploy SPAs as web services (unnecessary cost and latency).
5. [REQ] Use persistent disks for file storage on web services and background workers; disks are attached to the service and persist across deploys — set disk size in `render.yaml` with `disk: { size: <GB>, mountPath: <path> }`; never store persistent data in the container filesystem.
6. [REQ] Use private spaces for secure inter-service networking; services in the same private space communicate via internal hostnames (`<service-name>:<port>`) — never expose internal APIs via public URLs unless required; enable private spaces for production multi-service architectures.
7. [REQ] Use blue-green deploys for zero-downtime production releases; Render's preview deploys create a temporary instance for testing before promoting to production — use `render deploy --preview` for staging and promote via the Dashboard or CLI after verification.
8. [REQ] Deploy via Dockerfile for custom runtime requirements; set `dockerfilePath` in `render.yaml` or the Dashboard — ensure the Dockerfile exposes the correct port via `EXPOSE` and Render injects the `PORT` env var; never hardcode the port in the application (use `$PORT`).
9. [REQ] Set environment variables via `render.yaml` or the Dashboard; use `env_var_groups` for shared variables across services — mark secrets as `secret: true` in `render.yaml` and never commit secret values to the repository.
10. [REQ] Configure health checks via the service settings; set a health check path (HTTP endpoint returning 200) — Render uses health checks to determine service readiness and will roll back failed deploys if the health check fails within the grace period.
11. [PROHIBIT] Never store secrets in `render.yaml` plaintext — use secret env vars or env var groups; never use the container filesystem for persistent data without a disk; never deploy production services without a health check.
12. [PROHIBIT] Never expose database services via public URLs in production (use private spaces); never exceed disk size limits without upgrading the plan; never use free-tier services for production workloads (free-tier services spin down after inactivity).
[COMPAT]
- Render Platform 2024: `render.yaml` Blueprint GA, private spaces GA, Docker support GA.
- Runtimes: Node.js 18/20/22, Python 3.11/3.12, Ruby 3.2/3.3, Go 1.22, Rust 1.75.
- Databases: PostgreSQL 15/16 (managed), Redis 7 (managed).
[REFS]
- https://render.com/docs
- https://render.com/docs/blueprint-spec
- https://render.com/docs/web-services
- https://render.com/docs/disks
- https://render.com/docs/private-spaces
