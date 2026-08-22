[TECH] fly-io
[OBJ] Fly.io platform — apps, machines, volumes, secrets, networking, flyctl, multi-region, Postgres, SQLite LiteFS.
[RULES]
1. [REQ] Deploy applications as Fly.io apps via `flyctl deploy`; each app is defined by a `fly.toml` config file specifying build, services, and mounts — use Dockerfiles or Buildpacks for the build step; never deploy without a valid `fly.toml`.
2. [REQ] Use Fly Machines (not legacy shared-VM apps) for all new deployments; machines are independently scalable and restartable — use `fly machine` commands for lifecycle management and `fly scale` for horizontal scaling; set `min_machines_running` to keep warm instances.
3. [REQ] Use persistent volumes via `fly volumes create`; mount volumes in `fly.toml` under `[mounts]` with `source` and `destination` — volumes are region-specific and tied to a machine; never store persistent data in the machine filesystem without a volume.
4. [REQ] Set secrets via `fly secrets set <KEY>=<value>`; secrets are encrypted at rest and injected as environment variables at runtime — never commit secrets to `fly.toml` or the repository; use `fly secrets list` to audit (values are not shown).
5. [REQ] Configure networking via `fly.toml` `[services]` section; define `internal_port`, `protocol`, and `concurrency` settings — use Fly's built-in load balancer for multi-region traffic distribution; never expose internal ports directly without the Fly proxy.
6. [REQ] Use `flyctl` CLI for all operations; install via `curl -L https://fly.io/install.sh | sh` (Linux/macOS) or `pwsh -Command "iwr https://fly.io/install.ps1 | iex"` (Windows) — authenticate via `fly auth login` and never share auth tokens.
7. [REQ] Deploy multi-region by specifying `primary_region` in `fly.toml` and adding regions via `fly regions add`; use `fly scale --region` to distribute machines — configure health checks per region and handle failover via Fly's anycast networking.
8. [REQ] Use Fly Postgres for managed PostgreSQL; provision via `fly postgres create` and connect via the internal connection string (`<app>.internal:5432`) — use `fly postgres attach` to link the database to your app and inject `DATABASE_URL`; never connect to Fly Postgres via the public URL from internal services.
9. [REQ] Use LiteFS for distributed SQLite across regions; LiteFS replicates SQLite databases via a FUSE filesystem — configure in `fly.toml` with `[mounts]` and set the `LITEFS_PRIMARY` candidate; never write to non-primary LiteFS nodes (writes are forwarded but with higher latency).
10. [REQ] Configure health checks in `fly.toml` under `[[services.http_checks]]` or `[[services.tcp_checks]]`; set `interval`, `timeout`, and `grace_period` — Fly uses health checks to route traffic and restart unhealthy machines; never deploy without health checks.
11. [PROHIBIT] Never store secrets in `fly.toml` — use `fly secrets set`; never use the machine filesystem for persistent data without a volume; never deploy to a single region for production (use multi-region for HA).
12. [PROHIBIT] Never expose database internal ports publicly (use Fly private networking `.internal` DNS); never hardcode region names (use `primary_region` and `fly regions`); never exceed machine resource limits without scaling up the VM size.
[COMPAT]
- Fly.io Platform 2024: Fly Machines GA, `flyctl` v0.3.x, LiteFS v0.5.x.
- Runtimes: Any Docker-compatible image, Dockerfile or Buildpacks.
- Databases: Fly Postgres 15/16 (managed), LiteFS (distributed SQLite), Redis (Upstash integration).
[REFS]
- https://fly.io/docs/
- https://fly.io/docs/flyctl/
- https://fly.io/docs/postgres/
- https://fly.io/docs/litefs/
- https://fly.io/docs/machines/
