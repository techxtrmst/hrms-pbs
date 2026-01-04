FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  UV_COMPILE_BYTECODE=1 \
  UV_LINK_MODE=copy

# Install build dependencies
RUN apk add --no-cache --virtual .build-deps \
  build-base \
  postgresql-dev \
  libffi-dev \
  jpeg-dev \
  zlib-dev \
  freetype-dev \
  lcms2-dev \
  openjpeg-dev \
  tiff-dev \
  tk-dev \
  tcl-dev

# Copy dependency files
COPY requirements.txt ./

# Install dependencies with uv
RUN uv venv /app/.venv && \
  uv pip install --no-cache -r requirements.txt

# Production image
FROM python:3.13-alpine

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PATH="/app/.venv/bin:$PATH"

# Install runtime dependencies
RUN apk add --no-cache \
  postgresql-client \
  libpq \
  postgresql-dev \
  jpeg \
  zlib \
  freetype \
  lcms2 \
  openjpeg \
  tiff \
  curl && \
  adduser -D -u 1000 app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy and set permissions for entrypoint script first
COPY scripts/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Copy application code
COPY --chown=app:app . .

EXPOSE 8000

ENTRYPOINT ["/docker-entrypoint.sh"]
