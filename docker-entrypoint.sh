#!/usr/bin/env bash
set -e

# Create or migrate the knowledge base (idempotent; migrations back it up first).
mkdir -p /app/data/backups
uv run finsocnet kb init >/dev/null 2>&1 || uv run finsocnet kb migrate >/dev/null

exec "$@"
