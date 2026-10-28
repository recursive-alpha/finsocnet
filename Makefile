# FinSocNet Makefile
# Multi-Platform Financial Intelligence & Strategy Network

.PHONY: help install install-local web-install web-build web-dev web-start docker-build docker-up docker-down docker-logs docker-restart docker-ps db-init db-stats db-doctor clean

SHELL := /bin/bash

# Default target
help:
	@echo "=================================================================="
	@echo "    FinSocNet: Multi-Platform Intelligence & Strategy Stack       "
	@echo "=================================================================="
	@echo "Local Installation:"
	@echo "  make install        - Install Python CLI, register harnesses, and install web deps"
	@echo "  make install-local  - Install local session bridge prerequisites only"
	@echo ""
	@echo "Web UI (Next.js + TypeScript):"
	@echo "  make web-install    - Install npm dependencies in web/"
	@echo "  make web-build      - Build production Next.js application"
	@echo "  make web-dev        - Start Next.js development server on port 3000"
	@echo "  make web-start      - Start Next.js production server on port 3000"
	@echo ""
	@echo "Docker Stack:"
	@echo "  make docker-build   - Build container image (finsocnet:latest)"
	@echo "  make docker-up      - Start the full stack in background via docker compose"
	@echo "  make docker-down    - Stop and remove containers"
	@echo "  make docker-logs    - Follow container logs"
	@echo "  make docker-restart - Restart the container stack"
	@echo "  make docker-ps      - Check status of running containers"
	@echo ""
	@echo "Database & Knowledge Engine:"
	@echo "  make db-init        - Initialize SQLite database & migrations (data/knowledge.db)"
	@echo "  make db-stats       - Display database statistics and metrics"
	@echo "  make db-doctor      - Run database integrity and health check"
	@echo "  make clean          - Remove temporary caches and build artifacts"
	@echo "=================================================================="

# -------------------------------------------------------------
# Local Installation
# -------------------------------------------------------------

install: web-install
	@echo "==> Running FinSocNet installer..."
	./install.sh
	@echo "==> Local installation complete."

install-local:
	@echo "==> Installing local session export prerequisites..."
	./install.sh --local

# -------------------------------------------------------------
# Web UI
# -------------------------------------------------------------

web-install:
	@echo "==> Installing Web UI dependencies..."
	npm --prefix web install

web-build:
	@echo "==> Building Web UI for production..."
	npm --prefix web run build

web-dev:
	@echo "==> Starting Web UI development server on http://localhost:3000..."
	npm --prefix web run dev

web-start:
	@echo "==> Starting Web UI production server on http://localhost:3000..."
	npm --prefix web run start -- -p 3000 -H 0.0.0.0

# -------------------------------------------------------------
# Docker Operations
# -------------------------------------------------------------

docker-build:
	@echo "==> Building Docker image..."
	docker compose build

docker-up:
	@echo "==> Starting FinSocNet stack in detached mode..."
	docker compose up -d
	@echo "==> Stack is up! Web terminal available at http://localhost:$${PORT:-3001}"

docker-down:
	@echo "==> Stopping FinSocNet stack..."
	docker compose down

docker-logs:
	docker compose logs -f

docker-restart:
	@echo "==> Restarting FinSocNet stack..."
	docker compose restart

docker-ps:
	docker compose ps

# -------------------------------------------------------------
# Database & CLI
# -------------------------------------------------------------

db-init:
	@echo "==> Initializing SQLite knowledge base..."
	uv run finsocnet kb init

db-stats:
	@echo "==> Fetching database statistics..."
	uv run finsocnet kb stats

db-doctor:
	@echo "==> Running database doctor diagnostic check..."
	uv run finsocnet kb doctor

clean:
	@echo "==> Cleaning cache directories and build artifacts..."
	rm -rf web/.next web/out web/node_modules/.cache
	rm -rf __pycache__ finsocnet/__pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	@echo "==> Clean complete."
