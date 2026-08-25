# syntax=docker/dockerfile:1.7

# === Stage 1: Builder ===
FROM python:3.14-slim@sha256:03fa7aa0f269338f55f72dd1c06aa246f1b80d82d6f4d7ac2d6f8d5dad5c556 AS builder

# Create build user
RUN groupadd -r aios && useradd -r -g aios -m -d /app aios

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency files first for cache efficiency
COPY pyproject.toml README.md ./

# Install dependencies into a virtualenv for clean copy (production only, no dev)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e '.[graphify]'

# Copy source code
COPY runtime/ ./runtime/
COPY memory/ ./memory/
COPY aizee_mcp/ ./aizee_mcp/
COPY dashboard/ ./dashboard/
COPY aizee_cli.py config.py ./
COPY plugins.yaml ./
COPY scripts/validate-globals.py ./scripts/validate-globals.py

# Install the package itself
RUN pip install --no-cache-dir -e .

# === Stage 2: Runtime ===
FROM python:3.14-slim@sha256:03fa7aa0f269338f55f72dd1c06aa246f1b80d82d6f4d7ac2d6f8d5dad5c556 AS runtime

# Create non-root user
RUN groupadd -r aios && useradd -r -g aios -m -d /app aios

WORKDIR /app

# Copy virtualenv from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy static content
COPY AGENTS.md global-roles.md global-workflow.md manifest.json ./
COPY rules/ ./rules/
COPY tech-stack/ ./tech-stack/
COPY workflows/ ./workflows/
COPY skills/ ./skills/
COPY --from=builder /app/runtime/ ./runtime/
COPY --from=builder /app/memory/ ./memory/
COPY --from=builder /app/aizee_mcp/ ./aizee_mcp/
COPY --from=builder /app/dashboard/ ./dashboard/
COPY --from=builder /app/aizee_cli.py /app/config.py /app/plugins.yaml ./
COPY --from=builder /app/scripts/validate-globals.py ./scripts/validate-globals.py

# Create state directories
RUN mkdir -p state brain graphify-out && \
    chown -R aios:aios /app

# Validate all rule files (read-only check, no --fix to preserve reproducibility)
RUN python scripts/validate-globals.py || echo "Warning: some globals need fixing (non-blocking)"

# Persist state and generated indexes outside the image
VOLUME ["/app/state", "/app/brain", "/app/graphify-out"]

USER aios

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=5)" || exit 1

CMD ["python", "dashboard/server.py", "8080"]
