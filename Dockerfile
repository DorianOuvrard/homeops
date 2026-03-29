# Stage 1: Build React PWA
FROM node:22-alpine AS web-builder
WORKDIR /web
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY web/package.json web/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

# Stage 2: Python bot + FastAPI server
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation.
RUN pip install --no-cache-dir uv

# Copy dependency manifests + source for installation.
COPY pyproject.toml uv.lock ./
COPY bot/ ./bot/

# Install the package and its dependencies into the system Python.
# --no-cache avoids storing the uv cache layer inside the image.
RUN uv pip install --system --no-cache .

# Copy built React PWA to be served as static files.
COPY --from=web-builder /web/dist ./web/dist

# Create data directory for SQLite (ephemeral on CC, persistent with volumes).
RUN mkdir -p /data

# Expose FastAPI port
EXPOSE 8000

CMD ["python", "-m", "bot.main"]
