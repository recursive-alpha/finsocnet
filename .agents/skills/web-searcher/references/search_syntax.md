# Web Search Syntax & Operator Guide

## Search Operators for DuckDuckGo
- `site:x.com <query>`: Restricts search to X / Twitter profiles and tweets.
- `site:reddit.com <query>`: Restricts search to Reddit discussions and threads.
- `site:youtube.com <query>`: Restricts search to YouTube videos and playlists.
- `"exact phrase"`: Enforces strict verbatim phrase matching.
- `intitle:<word>`: Finds pages with the specified term in the page title.
- `-unwanted`: Excludes pages containing the given term.

## Examples
```bash
# Find X profile of a creator
uv run .agents/skills/web-searcher/scripts/search_web.py "Humbled Trader" --site x.com

# Find Reddit trading reviews
uv run .agents/skills/web-searcher/scripts/search_web.py "Qullamaggie swing trading rules" --site reddit.com
```
