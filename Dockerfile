# syntax=docker/dockerfile:1

# Build stage - using slim instead of Alpine for better torch/ML library compatibility
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted cache
ENV UV_LINK_MODE=copy

# Install build dependencies for packages that need compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libpq-dev \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/archives/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies - NO CACHE to avoid filling runner disk
RUN uv sync --frozen --no-dev --no-install-project --no-cache && \
    find /app/.venv -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && \
    find /app/.venv -type f -name '*.pyc' -delete 2>/dev/null || true && \
    find /app/.venv -type f -name '*.pyo' -delete 2>/dev/null || true

# Runtime stage
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libcairo2 \
    wkhtmltopdf \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy and set permissions for entrypoint script first
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy application code
COPY --chown=app:app . .

# Create necessary directories and set permissions
RUN mkdir -p /app/staticfiles /app/mediafiles /app/logs && \
    chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
