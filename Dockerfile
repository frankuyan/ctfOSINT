# SherlockML Production Dockerfile
# Multi-stage build for optimized image size

# =============================================================================
# Stage 1: Builder - Install dependencies and build package
# =============================================================================
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (for layer caching)
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels .

# Download SpaCy model
RUN pip install spacy && \
    python -m spacy download en_core_web_sm

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM python:3.11-slim as runtime

# Labels for container metadata
LABEL maintainer="SherlockML Team" \
      version="1.0.0" \
      description="OSINT Framework for CTF Competitions"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHERLOCKML_DATA=/data \
    SHERLOCKML_CONFIG=/config \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    tor \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash sherlockml

# Copy wheels from builder and install
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy SpaCy model from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages/en_core_web_sm \
    /usr/local/lib/python3.11/site-packages/en_core_web_sm

# Copy application code
COPY sherlockml/ ./sherlockml/
COPY pyproject.toml README.md ./

# Install the package
RUN pip install --no-cache-dir -e .

# Create necessary directories with correct permissions
RUN mkdir -p /data /config /home/sherlockml/.sherlockml && \
    chown -R sherlockml:sherlockml /app /data /config /home/sherlockml

# Copy default configuration
COPY --chown=sherlockml:sherlockml docker/config.default.yaml /config/config.yaml

# Volumes for persistent data
VOLUME ["/data", "/config"]

# Switch to non-root user
USER sherlockml

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD sherlockml --version || exit 1

# Default entrypoint
ENTRYPOINT ["sherlockml"]
CMD ["--help"]
