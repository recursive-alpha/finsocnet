#!/usr/bin/env bash
set -e

# Create or migrate the knowledge base (idempotent; migrations back it up first).
mkdir -p /app/data/backups
uv run finsocnet kb init >/dev/null 2>&1 || uv run finsocnet kb migrate >/dev/null

# The web UI talks to a warm local runner (python + embedding model stay loaded: ~50 ms per call instead of 1+ s).
if [ "$1" = "npm" ] && [ "${FINSOCNET_SERVE:-1}" = "1" ]; then
    finsocnet serve --port 8787 >/tmp/finsocnet-serve.log 2>&1 &
fi

exec "$@"
