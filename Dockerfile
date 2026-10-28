# syntax=docker/dockerfile:1
#
# One image for the whole stack: the finsocnet CLI (Python, uv), the skills (yt-dlp, ffmpeg) and the
# Next.js web UI, which calls the CLI. Runtime data (data/) is never copied in: it is a volume.

# -----------------------------------------------------------
# Stage 1: Python environment (locked, no dev extras)
# -----------------------------------------------------------
FROM python:3.12-slim-bookworm AS py-builder

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY finsocnet/ ./finsocnet/
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------
# Stage 2: Web frontend build
# -----------------------------------------------------------
FROM node:22-bookworm-slim AS web-builder

WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# -----------------------------------------------------------
# Stage 3: Runtime
# -----------------------------------------------------------
FROM python:3.12-slim-bookworm AS runner

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FINSOCNET_HOME=/app \
    KNOWLEDGE_DB_PATH=/app/data/knowledge.db \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_NO_SYNC=1 \
    NODE_ENV=production \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates git sqlite3 ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app
COPY --from=py-builder /app/.venv ./.venv
COPY pyproject.toml uv.lock README.md AGENTS.md ./
COPY finsocnet/ ./finsocnet/
COPY migrations/ ./migrations/
COPY config/ ./config/
COPY commands/ ./commands/
COPY evals/ ./evals/
COPY assets/ ./assets/
COPY specs/ ./specs/
COPY docs/ ./docs/
COPY .agents/ ./.agents/
COPY --from=web-builder /app/web/package.json /app/web/package-lock.json ./web/
COPY --from=web-builder /app/web/node_modules ./web/node_modules
COPY --from=web-builder /app/web/.next ./web/.next
COPY --from=web-builder /app/web/public ./web/public
COPY --from=web-builder /app/web/next.config.ts /app/web/tsconfig.json ./web/
COPY --from=web-builder /app/web/src ./web/src

COPY --chmod=0755 docker-entrypoint.sh /app/docker-entrypoint.sh
# The stack runs as the host user (compose `user:`), so everything must be readable by anyone whatever the host file modes are.
RUN mkdir -p /app/data && chmod -R a+rX /app

EXPOSE 3000
HEALTHCHECK --interval=20s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fs http://localhost:3000/api/stats || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["npm", "--prefix", "web", "run", "start", "--", "-p", "3000", "-H", "0.0.0.0"]
