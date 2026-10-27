---
name: reddit-explorer
description: Discover and explore Reddit trading communities (e.g. r/RealDayTrading, r/Daytrading, r/options), search discussions, and read full threads and top comments. Use when researching community sentiment, trader reviews, and public strategy critiques.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Reddit Explorer

Research tool for Reddit trading communities to explore subreddits, search for creator discussions, and extract thread texts with top community comments.

## Capabilities
1. **Subreddit Discovery:** Explore hot/top/new posts from subreddits (`r/RealDayTrading`, `r/Daytrading`, `r/SwingTrading`, `r/options`, `r/wallstreetbets`).
2. **Search Discussions:** Search across Reddit for creators (e.g., "Qullamaggie", "Humbled Trader"), tickers, or setups.
3. **Thread Reader:** Extracts original post body and top comments with scores.
4. **Knowledge DB Integration:** Automatically ingests threads and community insights into `data/knowledge.db` (`platform='reddit'`).

## Usage

### 1. Explore Subreddit Posts
```bash
uv run .agents/skills/reddit-explorer/scripts/explore_community.py "RealDayTrading" --sort hot --limit 5
```

### 2. Search Reddit Discussions
```bash
uv run .agents/skills/reddit-explorer/scripts/search_reddit.py "Qullamaggie 10 EMA strategy" --limit 5
```

### 3. Read Thread & Top Comments
```bash
uv run .agents/skills/reddit-explorer/scripts/read_thread.py "<REDDIT_THREAD_URL>" --ingest-db
```

## References
See [references/trading_subreddits.md](references/trading_subreddits.md) for a curated guide of high-signal trading communities.
