# syntax=docker/dockerfile:1

# -----------------------------------------------------------
# Stage 1: Base image with Python 3.12, Node.js 22, and uv
# -----------------------------------------------------------
FROM python:3.12-slim-bookworm AS base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FINSOCNET_HOME=/app \
    KNOWLEDGE_DB_PATH=/app/data/knowledge.db \
    PORT=3000 \
    HOST=0.0.0.0 \
    PATH="/app/.venv/bin:/root/.local/bin:$PATH"

WORKDIR /app

# Install system dependencies & Node.js 22
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    sqlite3 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv from official binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# -----------------------------------------------------------
# Stage 2: Python environment & package install
# -----------------------------------------------------------
FROM base AS py-builder

COPY pyproject.toml README.md ./
RUN uv sync --no-dev

# -----------------------------------------------------------
# Stage 3: Web frontend build
# -----------------------------------------------------------
FROM base AS web-builder

COPY web/package.json web/package-lock.json ./web/
RUN cd web && npm ci

COPY web/ ./web/
RUN cd web && npm run build

# -----------------------------------------------------------
# Stage 4: Production runtime
# -----------------------------------------------------------
FROM base AS runner

# Copy installed Python virtualenv
COPY --from=py-builder /app/.venv /app/.venv

# Copy Python codebase & specifications
COPY pyproject.toml README.md SPEC.md AGENTS.md install.sh ./
COPY finsocnet/ ./finsocnet/
COPY migrations/ ./migrations/
COPY legacy/ ./legacy/
COPY .agents/skills/ ./.agents/skills/
COPY data/persons/ ./data/persons/

# Copy built Web application and dependencies
COPY --from=web-builder /app/web/package.json /app/web/package-lock.json ./web/
COPY --from=web-builder /app/web/node_modules ./web/node_modules
COPY --from=web-builder /app/web/.next ./web/.next
COPY --from=web-builder /app/web/public ./web/public
COPY --from=web-builder /app/web/next.config.ts /app/web/tsconfig.json ./web/
COPY --from=web-builder /app/web/src ./web/src

# Create data directories with mount points
RUN mkdir -p /app/data/backups /app/data/audio /app/data/sessions

# Copy default database if present
COPY data/knowledge.db* /app/data/

# Copy entrypoint script
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:3000/api/stats || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["npm", "--prefix", "web", "run", "start", "--", "-p", "3000", "-H", "0.0.0.0"]
