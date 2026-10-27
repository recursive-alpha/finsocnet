---
name: x-explorer
description: Explore X (Twitter) profiles, search live posts, find traders and influencers, and extract tweet threads with optional authenticated login support. Use when searching X, gathering creator tweets, or tracking social market sentiment.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# X Explorer

Research tool for X (Twitter) to find traders, explore profiles, extract tweet threads, and search market discussions. Works in both authenticated and unauthenticated fallback modes.

## Capabilities
1. **Search X:** Search posts, tickers (`$SPY`, `$NVDA`), hashtags, and trader discussions.
2. **Profile Discovery:** Inspect user handles, bios, follower counts, and pinned/recent tweets.
3. **Optional Login:** Supports `auth_token` cookie or interactive browser login for live feeds and rate limit avoidance.
4. **Knowledge DB Integration:** Easily ingests discovered posts directly into `data/knowledge.db` (`platform='x'`).

## Usage

### 1. Explore User Profile
```bash
uv run .agents/skills/x-explorer/scripts/explore_user.py "@Qullamaggie" --ingest-db
```

### 2. Search Topics or Cashtags on X
```bash
uv run .agents/skills/x-explorer/scripts/search_x.py "breakout trading $NVDA" --limit 5
```

### 3. Configure Login / Session
```bash
# Save auth_token cookie from browser
uv run .agents/skills/x-explorer/scripts/login_x.py --token "<YOUR_AUTH_TOKEN>"

# Verify active session
uv run .agents/skills/x-explorer/scripts/login_x.py --verify
```

## References
See [references/x_auth_guide.md](references/x_auth_guide.md) for step-by-step authentication instructions.
