[TECH] railway
[OBJ] Railway platform — deploy from repo, databases, volumes, private networking, variables, multi-service, Railway CLI.
[RULES]
1. [REQ] Deploy from a Git repository connected to Railway; every push triggers a build using Nixpacks (auto-detected buildpack) or a Dockerfile — configure the build command and start command in the service settings or via `railway up`.
2. [REQ] Provision databases (PostgreSQL, MySQL, Redis, MongoDB) via Railway's template catalog or the Dashboard "New > Database" menu; databases run as managed services with automatic backups — never run databases as Docker containers inside a Railway app service.
3. [REQ] Use persistent volumes via `railway volume` or the Dashboard; mount volumes at a specified path for file storage — volumes are tied to the service and persist across redeployments; never store persistent data in the container filesystem without a volume.
4. [REQ] Use private networking for inter-service communication; Railway assigns each service a private hostname (`<service>.railway.internal`) — use private hostnames for database connections and API calls between services; never expose internal services via public domains unless required.
5. [REQ] Set environment variables via the Dashboard or CLI (`railway variables set`); use Railway Variables (plaintext) and Railway Secrets (encrypted) appropriately — reference other service variables via `${{<service>.<variable>}}` syntax for dynamic linking.
6. [REQ] Use multi-service architecture for microservices; each service has its own build, deploy, and scaling configuration — use `railway service add` or the Dashboard to create services and link them via private networking and shared variables.
7. [REQ] Use the Railway CLI (`railway`) for local development and deployment; run `railway link` to connect to a project, `railway run <command>` for local execution with remote env vars, and `railway up` for manual deploys — never use `railway up` for routine deploys in Git-connected projects.
8. [REQ] Configure health checks via the service settings; set a health check path (HTTP endpoint returning 200) or TCP port — Railway uses health checks to determine service readiness and restart unhealthy instances.
9. [REQ] Use Railway's built-in deployment metrics (CPU, memory, network) via the Dashboard; set up alerts for resource limits — never deploy without monitoring resource usage, especially for database services.
10. [REQ] Handle deployment failures by checking the deploy logs in the Dashboard; common issues include missing env vars, incorrect start commands, and build failures — use `railway logs` CLI for streaming logs during debugging.
11. [PROHIBIT] Never store secrets in plaintext environment variables visible in the Dashboard — use Railway Secrets; never expose database ports publicly (use private networking); never deploy without a health check configured.
12. [PROHIBIT] Never use the container filesystem for persistent data without a volume; never hardcode service hostnames (use Railway's private DNS); never exceed the plan's resource limits without upgrading.
[COMPAT]
- Railway Platform 2024: Nixpacks v3.x, Dockerfile support, private networking GA.
- CLI: `railway` v3.x (Node.js).
- Databases: PostgreSQL 15/16, MySQL 8, Redis 7, MongoDB 7.
[REFS]
- https://docs.railway.app/
- https://docs.railway.app/develop/services
- https://docs.railway.app/develop/private-networking
- https://docs.railway.app/reference/cli
- https://docs.railway.app/develop/volumes
