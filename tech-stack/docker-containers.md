# Tech-Stack: Docker Containers

> [!NOTE]
> **TRIGGER:** LOAD ON deployment setup, local environment creation, CI/CD pipeline building.
> **SCOPE:** Docker for SaaS, Multi-stage builds, PHP 8.4/8.5, FrankenPHP Octane, Node.js.

## 1. Build Optimization
- ALWAYS use Multi-stage Dockerfiles. Build assets in one stage (Node.js) and copy only the artifacts to the production image (PHP/FrankenPHP).
- Optimize layer caching by copying `composer.json`/`package.json` and installing dependencies before copying the rest of the application code.
- Implement strict `.dockerignore` files to prevent uploading `.git`, `node_modules`, and local `.env` files to the daemon.

## 2. Runtime & Security
- Run containers as non-root users wherever possible to enhance security.
- Define robust `HEALTHCHECK` instructions (e.g., curling a `/up` endpoint) for orchestration tools like ECS.
- Inject environment variables securely at runtime, avoiding hardcoding them in the image.

## 3. Local Development
- Use Docker Compose to orchestrate local environments mirroring production (Laravel 12/13, PostgreSQL 17, Redis 7).
- Mount volumes for local code to enable hot-reloading without rebuilding images.

## 4. Hard Constraints
- NEVER store secrets or credentials inside the Dockerfile.
- NEVER run background workers (Horizon) and the web server (Octane) in the same container process in production; split them into separate task definitions.
- ALWAYS tag images with git SHAs or semantic versions before pushing to ECR.

---

## ✅ DOCKER CONTAINERS COMPLIANCE CHECK (Mandatory)
- [ ] **Efficiency:** Are multi-stage builds and layer caching optimized?
- [ ] **Security:** Is the application running as a non-root user with no secrets in the image?
- [ ] **Orchestration:** Are health checks configured for production reliability?
