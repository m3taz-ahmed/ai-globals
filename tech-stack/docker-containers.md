[TECH] docker-containers
[OBJ] Docker Containers & Build Optimization.
[RULES]
1. [REQ] Build: Multi-stage Dockerfiles. Multi-Arch (`linux/amd64`, `linux/arm64`). Strict `.dockerignore`.
2. [REQ] Attestations: BuildKit SBOM and Provenance (`--sbom=true --provenance=mode=max`).
3. [REQ] Security: Run as non-root. `HEALTHCHECK` configured.
4. [PROHIBIT] Hard Constraints: NEVER store secrets in Dockerfile. NEVER run Horizon and Octane in the same process. ALWAYS tag images with Git SHAs.
