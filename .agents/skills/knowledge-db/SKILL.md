---
name: knowledge-db
description: Manage SQLite database (knowledge.db) and Chroma vector store for user profiles, content transcripts, trading hypotheses, and experiences across platforms (YouTube, TikTok, Facebook, X). Supports semantic vector search and RAG via Hugging Face embeddings.
license: MIT
metadata:
  version: "2.0.0"
  author: "finsocnet"
---

# Knowledge Database

Cross-platform relational and vector store for user/creator profiles, content transcripts, experiences, and structured hypotheses extracted from YouTube, TikTok, Facebook, X, and more.

## Core Tables
1. **`users`**: User/creator profile, handle, platform (`youtube`, `tiktok`, `facebook`, `x`, `podcast`), profile URL, and topics.
2. **`contents`**: Content ID, user ID, platform, title, URL, type (`video`, `post`, `thread`, `audio`), duration, description, transcript path.
3. **`hypotheses`**: Discrete trading rules, setups, holding periods, statistical claims, verbatim quotes, and timestamps.
4. **`skills`**: Catalog of synthesized Agent Skills mapped to users and platforms.

## Vector Collections (Chroma)
- **`hypotheses`**: Embedded hypothesis statements, setups, and quotes using `sentence-transformers/all-MiniLM-L6-v2`.
- **`content_chunks`**: Embedded ~30-second text/transcript chunks for semantic RAG retrieval.

## Usage

### 1. Ingest Video or Content Transcript
```bash
uv run .agents/skills/knowledge-db/scripts/db.py ingest-content data/transcripts/<content_id>.json --platform youtube
```

### 2. Ingest Hypotheses into Database & Vector Store
```bash
uv run .agents/skills/knowledge-db/scripts/db.py ingest-hypotheses data/hypotheses/<content_id>_hypotheses.json --platform youtube
```

### 3. Query & Vector Search
```bash
# Keyword / SQL filter
uv run .agents/skills/knowledge-db/scripts/db.py search --query "overnight" --platform youtube

# Semantic vector search on hypotheses
uv run .agents/skills/knowledge-db/scripts/db.py vector-search "should I hold overnight or close same day?" --limit 3

# RAG search across content transcript chunks
uv run .agents/skills/knowledge-db/scripts/db.py rag-search "semiconductor high ADR focus group" --limit 3

# Database stats
uv run .agents/skills/knowledge-db/scripts/db.py stats
```

## References
See [references/schema.sql](references/schema.sql) and [references/schema_guide.md](references/schema_guide.md) for table schemas and index details.
