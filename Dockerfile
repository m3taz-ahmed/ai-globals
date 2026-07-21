FROM python:3.11-slim

# Create non-root user for runtime security
RUN groupadd -r aios && useradd -r -g aios -m -d /app aios

WORKDIR /app

# Install dependencies as root, then drop privileges
COPY pyproject.toml README.md ./
COPY runtime/ ./runtime/
COPY memory/ ./memory/
COPY aios_mcp/ ./aios_mcp/
COPY dashboard/ ./dashboard/
COPY cli.py config.py ./
COPY plugins.yaml ./
COPY scripts/validate-globals.py ./scripts/validate-globals.py
COPY install.sh ./

RUN pip install --no-cache-dir -e '.[dev]' \
    && python scripts/validate-globals.py

# Copy static content last for cache efficiency
COPY AGENTS.md global-roles.md global-workflow.md manifest.json ./
COPY rules/ ./rules/
COPY tech-stack/ ./tech-stack/
COPY workflows/ ./workflows/
COPY skills/ ./skills/
RUN mkdir -p state brain graphify-out

RUN chown -R aios:aios /app
USER aios

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health')" || exit 1

CMD ["python", "dashboard/server.py", "8080"]
