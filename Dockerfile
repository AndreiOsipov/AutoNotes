# syntax=docker/dockerfile:1

# ---- Base stage: install dependencies ----
FROM python:3.12-slim-bookworm AS base

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy project config and install runtime dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# ---- Build stage: copy source code ----
FROM base AS builder

WORKDIR /app
COPY . .

# ---- Final stage ----
FROM base AS final

WORKDIR /app
COPY --from=builder /app .

# Create certs directory (mounted at runtime if needed)
RUN mkdir -p /app/certs

EXPOSE 8000

CMD ["uv", "run", "fastapi", "run", "src/main.py"]