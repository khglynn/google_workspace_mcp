FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Fleet ops (khglynn): upgrade base-image Python packaging residue flagged by
# Trivy — CVE-2026-24049 (wheel <0.46.2) + CVE-2026-23949 (jaraco.context <6.1.0)
RUN pip install --no-cache-dir --upgrade "wheel>=0.46.2" "setuptools>=81" "jaraco.context>=6.1.0"

COPY . .

# Install Python dependencies using uv sync
# Fleet ops (khglynn): +valkey extra — without it the Redis-backed OAuth proxy
# storage silently falls back to ephemeral disk (plan-adversary C1)
RUN uv sync --frozen --no-dev --extra disk --extra valkey

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# Give read and write access to the store_creds volume
RUN mkdir -p /app/store_creds \
    && chown -R app:app /app/store_creds \
    && chmod 755 /app/store_creds

USER app

# Expose port (use default of 8000 if PORT not set)
EXPOSE 8000
# Expose additional port if PORT environment variable is set to a different value
ARG PORT
EXPOSE ${PORT:-8000}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD sh -c 'curl -f http://localhost:${PORT:-8000}/health || exit 1'

# Set environment variables for Python startup args
ENV TOOL_TIER=""
ENV TOOLS=""

# Use entrypoint for the base command and CMD for args
ENTRYPOINT ["/bin/sh", "-c"]
CMD ["uv run main.py --transport streamable-http ${TOOL_TIER:+--tool-tier \"$TOOL_TIER\"} ${TOOLS:+--tools $TOOLS}"]
