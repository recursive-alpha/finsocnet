#!/usr/bin/env bash
set -e

# Initialize SQLite database if absent
if [ ! -f "${KNOWLEDGE_DB_PATH:-/app/data/knowledge.db}" ]; then
    echo "==> Knowledge base not found at ${KNOWLEDGE_DB_PATH:-/app/data/knowledge.db}. Initializing database..."
    uv run finsocnet kb init || true
fi

exec "$@"
