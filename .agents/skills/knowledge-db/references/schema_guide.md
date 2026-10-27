# Database Architecture & Query Guide

## SQLite Storage (`data/knowledge.db`)
- Normalized cross-platform model separating creators/users (`users`), content items (`contents`), and atomic trading rules/insights (`hypotheses`).
- Supports creators across YouTube, TikTok, Facebook, X, podcasts, and web.
- Foreign key constraints enabled to maintain relational integrity.
- Indexed on `user_id`, `content_id`, `platform`, `category`, and `direction`.

## Querying via Python CLI
```bash
# Initialize schema
uv run .agents/skills/knowledge-db/scripts/db.py init

# Full text search across hypotheses
uv run .agents/skills/knowledge-db/scripts/db.py search --query "overnight"

# Filter by direction, category, and platform
uv run .agents/skills/knowledge-db/scripts/db.py search --direction LONG --category holding_period --platform youtube

# Ingest content transcript
uv run .agents/skills/knowledge-db/scripts/db.py ingest-content data/transcripts/<content_id>.json --platform youtube

# Semantic vector search on hypotheses
uv run .agents/skills/knowledge-db/scripts/db.py vector-search "holding overnight vs intraday close" --limit 3

# RAG search across content transcript chunks
uv run .agents/skills/knowledge-db/scripts/db.py rag-search "momentum win rate" --limit 3
```
