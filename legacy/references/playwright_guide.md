# Playwright Web & Media Reader Guide

## Overview
Automated Chromium execution via Playwright to render single-page applications (React, Next.js, Vue), extract text articles, capture full-page screenshots, and inspect video/caption streams.

## CLI Usage
```bash
# Read web page content as clean text/markdown
uv run .agents/skills/web-reader/scripts/read_page.py "https://qullamaggie.com"

# Capture a full-page screenshot
uv run .agents/skills/web-reader/scripts/read_page.py "https://qullamaggie.com" --screenshot "data/screenshots/qullamaggie.png"

# Inspect a page for embedded videos and caption tracks (.vtt/.srt)
uv run .agents/skills/web-reader/scripts/inspect_video.py "https://qullamaggie.com"
```
