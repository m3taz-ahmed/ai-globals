[TECH] Docker Engine 29 (latest 29.7.2, Aug 2026)
[OBJ] Container runtime — experimental embedded containerd, `image` mount type non-experimental, `default-stop-timeout`, BuildKit 0.32.2, CVE fixes.
[RULES]
1. [REQ] Docker Engine 28 EOL 13 May 2026 — upgrade to Engine 29+ before EOL.
2. [REQ] `image` mount type is now non-experimental — use `--mount type=image,...` in `docker run` / `docker buildx` without experimental flag.
3. [REQ] Use `default-stop-timeout` config in `daemon.json` to set global container stop grace period — per-container `--stop-timeout` overrides.
4. [REQ] BuildKit 0.32.2 bundled — use `DOCKER_BUILDKIT=1` (default) or `docker buildx build` for multi-stage + multi-platform builds.
5. [REQ] Experimental embedded containerd — opt-in via `daemon.json` `features` flag; replaces containerd dependency for some use cases.
6. [REQ] Use multi-stage builds to minimize final image size — `FROM ... AS builder` + `FROM ... AS runtime`.
7. [REQ] Use `.dockerignore` to exclude files from build context — never send `node_modules` / `.git` to daemon.
8. [REQ] Use `docker compose` (v2 plugin) for multi-container apps — `docker-compose` v1 deprecated.
9. [REQ] Pin base image digests: `FROM node:22@sha256:...` — never use `:latest`.
10. [REQ] Use `HEALTHCHECK` in Dockerfiles for container health monitoring.
11. [REQ] Run containers as non-root user — `USER 1000` or `USER appuser`.
12. [REQ] Use `docker scan` or `trivy` for image vulnerability scanning in CI.
13. [PROHIBIT] Never use `:latest` tag in production — pin specific versions/digests.
14. [PROHIBIT] Never run containers as root — use non-root `USER`.
15. [PROHIBIT] Never use `docker-compose` v1 — use `docker compose` v2 plugin.
16. [PROHIBIT] Never use Engine 28 past EOL (13 May 2026) — upgrade to 29.
17. [CMD] `docker buildx build --platform linux/amd64,linux/arm64 -t img .` — multi-platform build.
18. [CMD] `docker compose up -d` — start stack.
19. [CMD] `docker run --mount type=image,source=img,target=/mnt img` — image mount (non-experimental).
20. [CMD] `docker scan img` — vulnerability scan.
[COMPAT]
- Docker Engine 29.7.2: latest (Aug 2026).
- Engine 28 EOL: 13 May 2026.
- BuildKit 0.32.2 bundled.
- `image` mount type: non-experimental (GA).
- Embedded containerd: experimental (opt-in).
- `default-stop-timeout`: new daemon config.
[REFS]
- https://docs.docker.com/engine/
- https://docs.docker.com/compose/
- https://docs.docker.com/build/
- https://docs.docker.com/engine/release-notes/
