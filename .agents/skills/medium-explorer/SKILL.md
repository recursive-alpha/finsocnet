---
name: medium-explorer
description: Explore Medium articles, authors, and topic tags (e.g. trading, algorithmic-trading, quantitative-finance), extract full story content, and manage browser session login state. Use when researching written trading strategies, quant blogs, and finance publications.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Medium Explorer

Research tool for Medium to explore financial publications, topic tags, and author profiles, and extract full-length trading and quantitative articles with automatic `knowledge.db` ingestion.

## Capabilities
1. **Topic Discovery:** Browse trending and latest articles under tags (`trading`, `algorithmic-trading`, `quantitative-finance`, `crypto`).
2. **Author Profile Inspection:** Extract author bios, follower stats, and story catalogs.
3. **Article Extraction:** Reads full article text (titles, headings, paragraphs, code blocks), bypassing visual paywall overlays.
4. **Browser Session Login:** Stores authenticated browser session states in `data/sessions/medium_session.json` for member-only access.
5. **Knowledge DB Integration:** Automatically ingests articles and author profiles into `data/knowledge.db` (`platform='medium'`).

## Usage

### 1. Explore Medium Topic Tag
```bash
uv run .agents/skills/medium-explorer/scripts/explore_tag.py "algorithmic-trading" --limit 5
```

### 2. Explore Author Profile
```bash
uv run .agents/skills/medium-explorer/scripts/explore_author.py "@ztraderai" --ingest-db
```

### 3. Read Full Article & Ingest into Knowledge DB
```bash
uv run .agents/skills/medium-explorer/scripts/read_article.py "https://medium.com/@ztraderai/what-is-data-cleaning-in-trading-00f164ca71a0" --ingest-db
```

### 4. Configure Browser Login (Optional)
```bash
uv run .agents/skills/medium-explorer/scripts/login_medium.py --interactive
```

## References
See [references/medium_topics.md](references/medium_topics.md) for top quantitative publications and tags.
