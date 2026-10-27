---
name: web-searcher
description: Search the public web using DuckDuckGo to discover creators, social profiles, trading discussions, and internet intelligence without API key requirements. Supports site filtering for x.com, reddit.com, and youtube.com.
license: MIT
metadata:
  version: "1.0.0"
  author: "finsocnet"
---

# Web Searcher

Public web search tool powered by DuckDuckGo with Playwright rendering fallback. Used for locating creator profiles, cross-platform accounts, trader discussions, and market research.

## Capabilities
- **No API Keys Required:** Queries DuckDuckGo directly with automatic fallback.
- **Site Filtering:** Dedicated shortcut for `site:x.com`, `site:reddit.com`, etc.
- **Structured JSON & Terminal Outputs:** Easily pipelined into other tools.

## Usage

### 1. General Search
```bash
uv run .agents/skills/web-searcher/scripts/search_web.py "Kristjan Qullamaggie 10 EMA strategy"
```

### 2. Discovering X / Twitter Profiles
```bash
uv run .agents/skills/web-searcher/scripts/search_web.py "Humbled Trader" --site x.com
```

### 3. Discovering Reddit Trading Discussions
```bash
uv run .agents/skills/web-searcher/scripts/search_web.py "Lance Breitstein Trillium" --site reddit.com
```

## References
See [references/search_syntax.md](references/search_syntax.md) for supported advanced search operators.
